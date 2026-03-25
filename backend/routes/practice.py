"""
练习记录 API（与核心比对解耦）。供成长轨迹与未来智能体使用。

关闭方式：环境变量 ENABLE_PRACTICE_API=false
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ..audio_processing.performance_metrics import (
    build_minimal_practice_metrics,
    build_practice_metrics,
)
from ..admin_auth import verify_admin_token
from ..auth_guard import require_login_user_id
from ..assistant_store import append_message
from ..paths import practice_data_dir
from ..practice_config import is_practice_api_enabled
from ..practice_store import (
    compute_summary,
    get_session,
    init_db,
    insert_event,
    insert_session,
    list_user_ids,
    list_events,
    list_sessions,
    update_session_extra,
)
from ..score_compare_service import dict_to_midi_note

router = APIRouter(prefix="/api/practice", tags=["practice"])


def _require_practice_api() -> None:
    if not is_practice_api_enabled():
        raise HTTPException(
            status_code=503,
            detail="练习记录 API 已关闭（设置 ENABLE_PRACTICE_API=true 可开启）",
        )


class PracticeEventCreate(BaseModel):
    event_type: str = Field(
        ...,
        description="事件类型，如 practice_start, session_end, skip_passage, user_tired",
        max_length=128,
    )
    score_id: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None, description="关联的练习会话 id")
    payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="任意 JSON 对象，如 {\"measure\": 4}",
    )


class PracticeSessionCreate(BaseModel):
    score_id: Optional[str] = Field(default=None, description="曲目 score_id")
    accuracy: float = Field(..., description="比对准确率")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="比对错误列表")
    compare_mode: Optional[str] = Field(
        default=None,
        description="比对模式：beginner_pitch_only 或 advanced_rhythm",
    )
    focus_start_measure: Optional[int] = Field(
        default=None,
        description="本次仅练习的起始小节（1-based，留空表示全曲）",
    )
    focus_end_measure: Optional[int] = Field(
        default=None,
        description="本次仅练习的结束小节（1-based，留空表示全曲）",
    )
    reference_notes: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="标准音符快照；与 played_notes 同时提供时可计算完整节奏指标",
    )
    played_notes: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="演奏音符快照",
    )
    practice_audio_id: Optional[str] = Field(
        default=None,
        description="由 /api/score/{id}/compare 返回，用于后续一键删除练习音频",
    )
    practice_audio_relpath: Optional[str] = Field(
        default=None,
        description="音频相对路径（由 compare 返回，服务端用于删除）",
    )


class TodayPlanRequest(BaseModel):
    score_id: Optional[str] = Field(default=None, description="曲目 ID；空则按最近会话自动选择")
    last_n: int = Field(default=20, ge=1, le=100, description="用于估计水平的窗口会话数")


class PracticeAudioDeleteBatchRequest(BaseModel):
    session_ids: List[str] = Field(default_factory=list, description="要删除音频的会话 ID 列表")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_today_tasks(
    summary: Dict[str, Any],
    *,
    compare_mode: Optional[str],
    focus_start: Optional[int],
    focus_end: Optional[int],
) -> List[Dict[str, Any]]:
    weak = summary.get("weak_measures_top") or []
    weak_measures: List[int] = []
    for w in weak[:3]:
        try:
            weak_measures.append(int(w.get("measure")))
        except (TypeError, ValueError, AttributeError):
            continue
    weak_measures = sorted(set(weak_measures))

    if weak_measures:
        start_m = min(weak_measures)
        end_m = max(weak_measures)
    else:
        start_m = focus_start
        end_m = focus_end

    tasks: List[Dict[str, Any]] = []
    if start_m is not None and end_m is not None:
        tasks.append(
            {
                "id": "focus_slow",
                "title": f"慢练第 {start_m}-{end_m} 小节",
                "minutes": 12,
                "steps": [
                    "双手拆分慢练，每遍保持稳定拍点",
                    "先追求正确率，再逐步加速",
                ],
                "apply": {
                    "focus_start_measure": start_m,
                    "focus_end_measure": end_m,
                },
            }
        )
    tasks.append(
        {
            "id": "record_recheck",
            "title": "同范围录制一遍并复盘错音",
            "minutes": 8,
            "steps": [
                "使用当前推荐范围录一遍",
                "观察错音类型是否下降（漏弹/错音/多弹）",
            ],
            "apply": {},
        }
    )
    mode = compare_mode or "beginner_pitch_only"
    if mode == "advanced_rhythm":
        tasks.append(
            {
                "id": "rhythm_metronome",
                "title": "节拍器稳定性训练",
                "minutes": 8,
                "steps": [
                    "60~72 BPM 下先稳拍再提速",
                    "关注起音均匀度和段落连贯",
                ],
                "apply": {"compare_mode": "advanced_rhythm"},
            }
        )
    else:
        tasks.append(
            {
                "id": "pitch_cleanup",
                "title": "音准清理训练",
                "minutes": 8,
                "steps": [
                    "低速确认每个音高与指法",
                    "优先降低漏弹和错音",
                ],
                "apply": {"compare_mode": "beginner_pitch_only"},
            }
        )
    return tasks[:4]


@router.post("/sessions")
async def practice_create_session(
    body: PracticeSessionCreate,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """
    写入一条练习记录。通常流程：
    1. POST /api/score/{id}/compare?include_note_snapshots=true
    2. 将响应中的 accuracy、errors、reference_notes、played_notes 提交到本接口
    """
    _require_practice_api()
    init_db()
    user_id = require_login_user_id(authorization)

    has_snapshots = (
        body.reference_notes
        and body.played_notes
        and len(body.reference_notes) > 0
        and len(body.played_notes) > 0
    )
    if body.compare_mode == "beginner_pitch_only":
        metrics = build_minimal_practice_metrics(body.accuracy, body.errors)
    elif has_snapshots:
        try:
            ref = [dict_to_midi_note(d) for d in body.reference_notes]  # type: ignore[arg-type]
            play = [dict_to_midi_note(d) for d in body.played_notes]  # type: ignore[arg-type]
        except (KeyError, TypeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"音符序列格式无效: {e}")
        metrics = build_practice_metrics(ref, play, body.accuracy, body.errors)
    else:
        metrics = build_minimal_practice_metrics(body.accuracy, body.errors)

    extra: Optional[Dict[str, Any]] = None
    if body.focus_start_measure is not None or body.focus_end_measure is not None:
        extra = {}
        if body.focus_start_measure is not None:
            extra["focus_start_measure"] = int(body.focus_start_measure)
        if body.focus_end_measure is not None:
            extra["focus_end_measure"] = int(body.focus_end_measure)
    if body.compare_mode:
        if extra is None:
            extra = {}
        extra["compare_mode"] = body.compare_mode
    if body.practice_audio_id:
        if extra is None:
            extra = {}
        aid = str(body.practice_audio_id).strip()
        if aid:
            extra["practice_audio_id"] = aid
            relpath = str(body.practice_audio_relpath or "").strip()
            if relpath:
                extra["practice_audio_relpath"] = relpath
            extra["practice_audio_deleted"] = False

    session_id = insert_session(
        user_id,
        metrics,
        body.errors,
        score_id=body.score_id,
        extra=extra,
    )
    return {"session_id": session_id, "metrics": metrics}


@router.get("/sessions")
async def practice_list_sessions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    score_id: Optional[str] = Query(None, description="按曲目筛选"),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _require_practice_api()
    init_db()
    user_id = require_login_user_id(authorization)
    sessions = list_sessions(user_id, limit=limit, offset=offset, score_id=score_id)
    return {"user_id": user_id, "sessions": sessions, "count": len(sessions)}


@router.get("/sessions/{session_id}")
async def practice_get_session(
    session_id: str,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _require_practice_api()
    init_db()
    user_id = require_login_user_id(authorization)
    s = get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(s.get("user_id") or "") != user_id:
        raise HTTPException(status_code=403, detail="无权限访问该会话")
    return s


@router.delete("/sessions/{session_id}/audio")
async def practice_delete_session_audio(
    session_id: str,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _require_practice_api()
    init_db()
    user_id = require_login_user_id(authorization)
    s = get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(s.get("user_id") or "") != user_id:
        raise HTTPException(status_code=403, detail="无权限删除该会话音频")
    extra = dict(s.get("extra") or {})
    relpath = str(extra.get("practice_audio_relpath") or "").strip()
    if not relpath:
        return {"session_id": session_id, "deleted": False, "reason": "no_audio"}
    target = (practice_data_dir() / relpath).resolve()
    root = practice_data_dir().resolve()
    if str(target).startswith(str(root)) and target.exists():
        try:
            target.unlink(missing_ok=True)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除音频失败: {e}") from e
    extra["practice_audio_deleted"] = True
    extra["practice_audio_deleted_at"] = _utc_now_iso()
    update_session_extra(session_id, extra)
    return {"session_id": session_id, "deleted": True}


@router.post("/audio/delete-batch")
async def practice_delete_audio_batch(
    body: PracticeAudioDeleteBatchRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _require_practice_api()
    init_db()
    user_id = require_login_user_id(authorization)
    deleted: List[str] = []
    failed: List[Dict[str, str]] = []
    for sid_raw in body.session_ids:
        sid = str(sid_raw or "").strip()
        if not sid:
            continue
        s = get_session(sid)
        if not s:
            failed.append({"session_id": sid, "reason": "not_found"})
            continue
        if str(s.get("user_id") or "") != user_id:
            failed.append({"session_id": sid, "reason": "forbidden"})
            continue
        extra = dict(s.get("extra") or {})
        relpath = str(extra.get("practice_audio_relpath") or "").strip()
        if not relpath:
            failed.append({"session_id": sid, "reason": "no_audio"})
            continue
        target = (practice_data_dir() / relpath).resolve()
        root = practice_data_dir().resolve()
        if str(target).startswith(str(root)) and target.exists():
            try:
                target.unlink(missing_ok=True)
            except Exception:
                failed.append({"session_id": sid, "reason": "unlink_failed"})
                continue
        extra["practice_audio_deleted"] = True
        extra["practice_audio_deleted_at"] = _utc_now_iso()
        update_session_extra(sid, extra)
        deleted.append(sid)
    return {"deleted_count": len(deleted), "failed_count": len(failed), "deleted": deleted, "failed": failed}


@router.get("/summary")
async def practice_summary(
    score_id: Optional[str] = Query(None, description="仅统计该曲目"),
    last_n: int = Query(30, ge=1, le=200, description="最近 N 条会话"),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """聚合最近若干次练习会话（准确率、错误数、节奏摘要、薄弱小节 Top）。"""
    _require_practice_api()
    init_db()
    user_id = require_login_user_id(authorization)
    return compute_summary(user_id, score_id=score_id, last_n=last_n)


@router.post("/events")
async def practice_create_event(
    body: PracticeEventCreate,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """记录结构化事件（与比对解耦，供后续分析或智能体使用）。"""
    _require_practice_api()
    init_db()
    user_id = require_login_user_id(authorization)
    et = (body.event_type or "").strip()
    if not et:
        raise HTTPException(status_code=400, detail="event_type 不能为空")
    eid = insert_event(
        user_id,
        et,
        score_id=body.score_id,
        session_id=body.session_id,
        payload=body.payload,
    )
    if et in {"task_completed", "task_skipped", "task_failed"}:
        try:
            note = {
                "task_completed": "任务已完成",
                "task_skipped": "任务被跳过",
                "task_failed": "任务未完成",
            }.get(et, et)
            append_message(
                user_id,
                "assistant",
                f"系统记录：{note}。事件详情：{body.payload or {}}",
                meta={"source": "practice_event", "event_type": et},
            )
        except Exception:
            # 会话同步失败不影响主流程
            pass
    return {"event_id": eid}


@router.get("/events")
async def practice_list_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None, description="按类型筛选"),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _require_practice_api()
    init_db()
    user_id = require_login_user_id(authorization)
    events = list_events(user_id, limit=limit, offset=offset, event_type=event_type)
    return {"user_id": user_id, "events": events, "count": len(events)}


@router.get("/users")
async def practice_list_users(
    limit: int = Query(100, ge=1, le=1000),
    x_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """返回有练习数据的用户列表（用于管理端切换）。"""
    _require_practice_api()
    if not verify_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="管理员鉴权失败")
    init_db()
    users = list_user_ids(limit=limit)
    return {"users": users, "count": len(users)}


@router.post("/today-plan")
async def practice_today_plan(
    body: TodayPlanRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """
    生成今日任务单（阶段 3 第 1 步：生成与展示，不含打卡提交）。
    """
    _require_practice_api()
    init_db()
    user_id = require_login_user_id(authorization)

    score_id = body.score_id
    latest_meta: Dict[str, Any] = {}
    latest = list_sessions(user_id, limit=1, offset=0, score_id=score_id)
    if not score_id and latest:
        score_id = latest[0].get("score_id")
    if score_id:
        latest = list_sessions(user_id, limit=1, offset=0, score_id=score_id)
    if latest:
        full = get_session(latest[0]["id"])
        if full:
            extra = full.get("extra") or {}
            latest_meta = {
                "compare_mode": extra.get("compare_mode"),
                "focus_start_measure": extra.get("focus_start_measure"),
                "focus_end_measure": extra.get("focus_end_measure"),
                "session_id": full.get("id"),
            }

    summary = compute_summary(user_id, score_id=score_id, last_n=body.last_n)
    tasks = _build_today_tasks(
        summary,
        compare_mode=latest_meta.get("compare_mode"),
        focus_start=latest_meta.get("focus_start_measure"),
        focus_end=latest_meta.get("focus_end_measure"),
    )
    total_minutes = int(sum(int(t.get("minutes") or 0) for t in tasks))
    try:
        append_message(
            user_id,
            "assistant",
            "系统记录：已生成今日任务单。",
            meta={
                "source": "today_plan",
                "score_id": score_id,
                "total_minutes": total_minutes,
                "tasks": tasks,
            },
        )
    except Exception:
        # 会话同步失败不影响主流程
        pass
    return {
        "user_id": user_id,
        "score_id": score_id,
        "last_n": body.last_n,
        "summary_snapshot": {
            "window_sessions": summary.get("window_sessions", 0),
            "accuracy_mean": (summary.get("accuracy") or {}).get("mean"),
            "weak_measures_top": summary.get("weak_measures_top") or [],
            "latest_compare_mode": latest_meta.get("compare_mode"),
        },
        "total_minutes": total_minutes,
        "tasks": tasks,
    }
