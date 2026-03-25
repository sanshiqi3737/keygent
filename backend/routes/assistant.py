"""
智能练习建议（阶段 1：仅文本，不调软件）。

依赖环境变量 DASHSCOPE_API_KEY（阿里云百炼）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..assistant_store import (
    append_message,
    ensure_thread,
    list_messages,
)
from ..auth_guard import require_login_user_id
from ..assistant_config import get_assistant_model, get_dashscope_api_key
from ..assistant_service import (
    generate_assistant_chat_reply,
    generate_practice_suggestion,
)
from ..paths import scores_data_dir
from ..practice_store import compute_summary, get_session, init_db, list_sessions

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class AssistantSuggestRequest(BaseModel):
    user_id: str = Field(default="default", description="与练习记录一致")
    score_id: Optional[str] = Field(default=None, description="仅针对该曲目；空则统计全部")
    last_n: int = Field(default=20, ge=1, le=100, description="概况窗口会话数")


class AssistantThreadRequest(BaseModel):
    user_id: str = Field(default="default", description="用户 ID")
    limit: int = Field(default=40, ge=1, le=200, description="返回消息条数")


class AssistantMessageRequest(BaseModel):
    user_id: str = Field(default="default", description="用户 ID")
    content: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    score_id: Optional[str] = Field(default=None, description="当前曲目")
    last_n: int = Field(default=20, ge=1, le=100, description="摘要窗口")


_DIFF_RANK = {
    "very_easy": 1,
    "easy": 2,
    "medium": 3,
    "hard": 4,
    "very_hard": 5,
}


def _rank_to_difficulty(rank: int) -> str:
    m = {1: "very_easy", 2: "easy", 3: "medium", 4: "hard", 5: "very_hard"}
    return m.get(max(1, min(5, int(rank))), "easy")


def _estimate_user_level(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    基于近期表现估计用户水平（0~1）与 1~5 档位。
    """
    acc_mean = None
    try:
        acc_obj = summary.get("accuracy") or {}
        if acc_obj.get("mean") is not None:
            acc_mean = float(acc_obj["mean"])
    except (TypeError, ValueError):
        acc_mean = None

    comp_mean = None
    try:
        stab = summary.get("stability_across_sessions") or {}
        if stab.get("composite_stability_mean") is not None:
            comp_mean = float(stab["composite_stability_mean"])
    except (TypeError, ValueError):
        comp_mean = None

    # 加权：准确率主导，稳定性辅助（缺失时自动降级）
    score = 0.5
    if acc_mean is not None and comp_mean is not None:
        score = 0.72 * acc_mean + 0.28 * comp_mean
    elif acc_mean is not None:
        score = acc_mean
    elif comp_mean is not None:
        score = comp_mean
    score = max(0.0, min(1.0, float(score)))

    # 1~5 档：very_easy -> very_hard
    rank = int(round(1 + score * 4))
    rank = max(1, min(5, rank))
    return {
        "score": round(score, 4),
        "rank": rank,
        "label": _rank_to_difficulty(rank),
    }


def _relative_difficulty(user_rank: int, piece_difficulty: Optional[str]) -> Dict[str, Any]:
    pr = _DIFF_RANK.get((piece_difficulty or "").lower(), 3)
    gap = int(pr - max(1, min(5, int(user_rank))))
    if gap >= 2:
        txt = "明显偏难"
    elif gap == 1:
        txt = "略有挑战"
    elif gap == 0:
        txt = "基本匹配"
    elif gap == -1:
        txt = "略偏容易"
    else:
        txt = "明显偏容易"
    return {"gap": gap, "text": txt, "piece_rank": pr}


def _list_available_score_ids(limit: int = 30) -> List[str]:
    """
    轻量曲库候选：读取 data/scores 下已上传曲目目录（按目录 mtime 倒序）。
    """
    if not scores_data_dir().exists():
        return []
    dirs = [p for p in scores_data_dir().iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out: List[str] = []
    for d in dirs[: max(1, limit)]:
        out.append(d.name)
    return out


def _normalize_abilities(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for x in raw:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
    # preserve order, drop duplicates
    seen = set()
    uniq: List[str] = []
    for a in out:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    return uniq


def _read_score_profile(score_id: str) -> Dict[str, Any]:
    """
    读取曲目元信息（若无 meta.json 则返回默认结构）。
    meta.json 示例:
      {"title":"车尔尼599 No.1","difficulty":"easy","abilities":["rhythm_stability","left_hand_control"]}
    """
    root = scores_data_dir() / score_id
    profile: Dict[str, Any] = {
        "score_id": score_id,
        "title": score_id,
        "difficulty": None,
        "abilities": [],
    }
    meta = root / "meta.json"
    if not meta.exists():
        return profile
    try:
        obj = json.loads(meta.read_text(encoding="utf-8"))
    except Exception:
        return profile
    if isinstance(obj, dict):
        title = obj.get("title")
        if isinstance(title, str) and title.strip():
            profile["title"] = title.strip()
        d = obj.get("difficulty")
        if isinstance(d, str) and d.strip():
            dd = d.strip().lower()
            profile["difficulty"] = dd
        profile["abilities"] = _normalize_abilities(obj.get("abilities"))
    return profile


def _target_difficulty(acc_mean: Optional[float]) -> str:
    if acc_mean is None:
        return "easy"
    if acc_mean < 0.70:
        return "very_easy"
    if acc_mean < 0.85:
        return "easy"
    if acc_mean < 0.93:
        return "medium"
    return "hard"


def _recommend_next_score(
    *,
    current_ids: List[str],
    target_difficulty: str,
    target_abilities: List[str],
    pool: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    target_rank = _DIFF_RANK.get(target_difficulty, 2)
    cur = {x for x in current_ids if x}
    best: Optional[Dict[str, Any]] = None
    best_key: Optional[tuple] = None
    target_ability_set = set(target_abilities)
    for p in pool:
        sid = p.get("score_id")
        if not isinstance(sid, str) or sid in cur:
            continue
        diff = p.get("difficulty")
        rank = _DIFF_RANK.get(diff, 3) if isinstance(diff, str) else 3
        dist = abs(rank - target_rank)
        abilities = p.get("abilities") if isinstance(p.get("abilities"), list) else []
        overlap = len(set(abilities) & target_ability_set)
        # 优先能力重合，其次难度距离，最后按 score_id 字典序保证稳定
        k = (-overlap, dist, sid)
        if best_key is None or k < best_key:
            best_key = k
            best = p
    return best


def _build_structured_plan(
    summary: Dict[str, Any],
    latest_session_meta: Dict[str, Any],
    preferred_score_id: Optional[str] = None,
    available_score_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    阶段 2：规则先行的结构化计划（LLM 仅负责润色说明）。
    """
    weak = summary.get("weak_measures_top") or []
    weak_measures: List[int] = []
    for item in weak[:3]:
        try:
            weak_measures.append(int(item.get("measure")))
        except (TypeError, ValueError, AttributeError):
            continue
    weak_measures = sorted(set(weak_measures))

    focus_start = min(weak_measures) if weak_measures else None
    focus_end = max(weak_measures) if weak_measures else None
    if focus_start is None or focus_end is None:
        focus_start = latest_session_meta.get("focus_start_measure")
        focus_end = latest_session_meta.get("focus_end_measure")

    acc_mean = None
    acc = summary.get("accuracy") or {}
    if acc.get("mean") is not None:
        try:
            acc_mean = float(acc["mean"])
        except (TypeError, ValueError):
            acc_mean = None

    # 默认：初级模式优先，分数较高且有节奏统计时可建议高级
    rhythm_block = summary.get("rhythm") or {}
    has_rhythm_sessions = int(rhythm_block.get("sessions_with_rhythm_score") or 0) > 0
    suggested_mode = "beginner_pitch_only"
    if acc_mean is not None and acc_mean >= 0.90 and has_rhythm_sessions:
        suggested_mode = "advanced_rhythm"

    today_minutes = 25
    if acc_mean is not None:
        if acc_mean < 0.70:
            today_minutes = 35
        elif acc_mean < 0.85:
            today_minutes = 30
        else:
            today_minutes = 20

    steps: List[str] = []
    if focus_start is not None and focus_end is not None:
        steps.append(f"先练第 {focus_start}-{focus_end} 小节，慢速 3~5 遍。")
    steps.append("再用同范围录一遍，观察错音类型是否减少。")
    if suggested_mode == "beginner_pitch_only":
        steps.append("当前建议使用“初级（仅看音准）”模式，先把错音压下来。")
    else:
        steps.append("可切到“高级（音准+节奏）”模式，配合节拍器稳定起音。")

    reasons = []
    if weak_measures:
        reasons.append(
            "窗口内薄弱小节 Top: " + ", ".join(str(m) for m in weak_measures)
        )
    if acc_mean is not None:
        reasons.append(f"窗口内准确率均值: {round(acc_mean * 100, 1)}%")
    if latest_session_meta.get("compare_mode"):
        reasons.append(f"最近一次模式: {latest_session_meta['compare_mode']}")
    target_abilities: List[str] = []
    if suggested_mode == "beginner_pitch_only":
        target_abilities = ["pitch_accuracy", "slow_practice_control"]
    else:
        target_abilities = ["rhythm_stability", "tempo_control"]

    actions: List[Dict[str, Any]] = []
    if focus_start is not None and focus_end is not None:
        actions.append(
            {
                "type": "set_focus_measures",
                "label": f"应用推荐小节 {focus_start}-{focus_end}",
                "payload": {"focus_start_measure": focus_start, "focus_end_measure": focus_end},
            }
        )
    actions.append(
        {
            "type": "set_compare_mode",
            "label": "应用推荐比对模式",
            "payload": {"compare_mode": suggested_mode},
        }
    )
    target_score_id = preferred_score_id or latest_session_meta.get("score_id")
    user_level = _estimate_user_level(summary)
    reasons.append(
        f"用户水平估计: {user_level['label']}（score={user_level['score']}）"
    )
    if isinstance(target_score_id, str) and target_score_id:
        target_profile = _read_score_profile(target_score_id)
        rd = _relative_difficulty(user_level["rank"], target_profile.get("difficulty"))
        actions.append(
            {
                "type": "open_score_page",
                "label": "去练这首",
                "payload": {"score_id": target_score_id},
            }
        )
        reasons.append(
            f"当前曲目匹配度: {rd['text']}（曲目难度: {target_profile.get('difficulty') or 'unknown'}）"
        )
    recommended_next_score_id: Optional[str] = None
    recommended_next_score_profile: Optional[Dict[str, Any]] = None
    pool = available_score_ids or []
    if pool:
        profile_pool = [_read_score_profile(sid) for sid in pool if isinstance(sid, str) and sid]
        current_ids = [
            str(x)
            for x in (preferred_score_id, latest_session_meta.get("score_id"))
            if isinstance(x, str) and x
        ]
        target_diff = _target_difficulty(acc_mean)
        pick = _recommend_next_score(
            current_ids=current_ids,
            target_difficulty=target_diff,
            target_abilities=target_abilities,
            pool=profile_pool,
        )
        if pick:
            recommended_next_score_id = pick.get("score_id")
            recommended_next_score_profile = pick
    if recommended_next_score_id:
        actions.append(
            {
                "type": "open_score_page",
                "label": "去练推荐下一首",
                "payload": {"score_id": recommended_next_score_id},
            }
        )
        rec_title = (recommended_next_score_profile or {}).get("title") or recommended_next_score_id
        rec_diff = (recommended_next_score_profile or {}).get("difficulty")
        rec_ab = (recommended_next_score_profile or {}).get("abilities") or []
        rec_rd = _relative_difficulty(user_level["rank"], rec_diff)
        reasons.append(f"推荐下一首候选: {rec_title}")
        if rec_diff:
            reasons.append(
                f"候选难度: {rec_diff}（目标难度: {_target_difficulty(acc_mean)}，对你{rec_rd['text']}）"
            )
        if rec_ab:
            reasons.append("候选能力标签: " + ", ".join(str(x) for x in rec_ab[:4]))

    return {
        "today_minutes": today_minutes,
        "suggested_compare_mode": suggested_mode,
        "focus_start_measure": focus_start,
        "focus_end_measure": focus_end,
        "recommended_next_score_id": recommended_next_score_id,
        "recommended_training_abilities": target_abilities,
        "recommended_next_score": recommended_next_score_profile,
        "user_level_estimate": user_level,
        "relative_difficulty": {
            "current_score": _relative_difficulty(
                user_level["rank"],
                (_read_score_profile(target_score_id).get("difficulty") if isinstance(target_score_id, str) and target_score_id else None),
            ) if isinstance(target_score_id, str) and target_score_id else None,
            "recommended_next_score": _relative_difficulty(
                user_level["rank"],
                (recommended_next_score_profile or {}).get("difficulty"),
            ) if recommended_next_score_profile else None,
        },
        "steps": steps,
        "actions": actions,
        "reasons": reasons,
    }


def _build_local_fallback_text(
    summary: Dict[str, Any],
    plan: Dict[str, Any],
    *,
    user_message: Optional[str] = None,
) -> str:
    """
    无百炼 Key 时的本地兜底建议，避免助手功能直接不可用。
    """
    acc_mean = None
    try:
        acc_obj = summary.get("accuracy") or {}
        if acc_obj.get("mean") is not None:
            acc_mean = float(acc_obj["mean"])
    except (TypeError, ValueError):
        acc_mean = None

    reasons = [str(x) for x in (plan.get("reasons") or []) if str(x).strip()][:3]
    actions = [str(x) for x in (plan.get("actions") or []) if str(x).strip()][:3]
    steps = [str(x) for x in (plan.get("steps") or []) if str(x).strip()][:3]

    lines: List[str] = ["当前为离线建议模式（未配置百炼 API Key）。"]
    if user_message:
        lines.append(f"你刚才的问题：{user_message}")
    if acc_mean is not None:
        lines.append(f"近期准确率均值约 {round(acc_mean * 100, 1)}%。")
    if reasons:
        lines.append("判断依据：")
        lines.extend([f"- {x}" for x in reasons])
    if actions:
        lines.append("建议动作：")
        lines.extend([f"- {x}" for x in actions])
    elif steps:
        lines.append("建议动作：")
        lines.extend([f"- {x}" for x in steps])
    lines.append("如需更细致的自然语言点评，请在环境变量中配置 DASHSCOPE_API_KEY。")
    return "\n".join(lines)


@router.post("/suggest")
async def assistant_suggest(
    body: AssistantSuggestRequest,
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    """
    根据近期练习概况（及最近一次会话的错音抽样）调用通义生成中文练习建议。
    """
    user_id = require_login_user_id(authorization)
    init_db()
    summary = compute_summary(user_id, score_id=body.score_id, last_n=body.last_n)

    err_sample: List[Dict[str, Any]] = []
    latest_session_meta: Dict[str, Any] = {}
    sessions = list_sessions(user_id, limit=1, offset=0, score_id=body.score_id)
    if sessions:
        full = get_session(sessions[0]["id"])
        if full and full.get("errors"):
            extra = full.get("extra") or {}
            latest_session_meta = {
                "session_id": full.get("id"),
                "score_id": sessions[0].get("score_id"),
                "created_at": full.get("created_at"),
                "compare_mode": extra.get("compare_mode"),
                "focus_start_measure": extra.get("focus_start_measure"),
                "focus_end_measure": extra.get("focus_end_measure"),
            }
            try:
                focus_start = int(extra["focus_start_measure"]) if extra.get("focus_start_measure") is not None else None
            except (TypeError, ValueError, KeyError):
                focus_start = None
            try:
                focus_end = int(extra["focus_end_measure"]) if extra.get("focus_end_measure") is not None else None
            except (TypeError, ValueError, KeyError):
                focus_end = None

            for e in full["errors"][:25]:
                if isinstance(e, dict):
                    m = e.get("measure")
                    if (focus_start is not None or focus_end is not None):
                        if m is None:
                            continue
                        try:
                            m_int = int(m)
                        except (TypeError, ValueError):
                            continue
                        if focus_start is not None and m_int < focus_start:
                            continue
                        if focus_end is not None and m_int > focus_end:
                            continue

                    err_sample.append(
                        {
                            k: e.get(k)
                            for k in ("type", "measure", "expected_name", "played_name", "time")
                            if e.get(k) is not None
                        }
                    )

    candidate_scores = _list_available_score_ids(limit=30)
    plan = _build_structured_plan(
        summary,
        latest_session_meta,
        preferred_score_id=body.score_id,
        available_score_ids=candidate_scores,
    )
    if not get_dashscope_api_key():
        return {
            "suggestion": _build_local_fallback_text(summary, plan),
            "model": "local-rule-fallback",
            "plan": plan,
        }

    try:
        text = await generate_practice_suggestion(
            summary,
            err_sample,
            score_id=body.score_id,
            latest_session_meta=latest_session_meta,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {
        "suggestion": text,
        "model": get_assistant_model(),
        "plan": plan,
    }


@router.get("/thread")
async def assistant_thread(
    limit: int = 40,
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    user_id = require_login_user_id(authorization)
    th = ensure_thread(user_id)
    messages = list_messages(user_id, limit=max(1, min(limit, 200)))
    return {"thread": th, "messages": messages}


@router.post("/message")
async def assistant_message(
    body: AssistantMessageRequest,
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    user_id = require_login_user_id(authorization)
    user_msg = append_message(
        user_id,
        "user",
        body.content.strip(),
        meta={"score_id": body.score_id},
    )
    summary = compute_summary(user_id, score_id=body.score_id, last_n=body.last_n)
    history_raw = list_messages(user_id, limit=30)
    history = [
        {"role": str(m.get("role")), "content": str(m.get("content"))}
        for m in history_raw
        if m.get("role") in {"user", "assistant"} and m.get("content")
    ]
    if not get_dashscope_api_key():
        candidate_scores = _list_available_score_ids(limit=30)
        plan = _build_structured_plan(
            summary,
            {"score_id": body.score_id, "compare_mode": None},
            preferred_score_id=body.score_id,
            available_score_ids=candidate_scores,
        )
        reply = _build_local_fallback_text(
            summary,
            plan,
            user_message=body.content.strip(),
        )
        asst_msg = append_message(
            user_id,
            "assistant",
            reply,
            meta={"source": "local_fallback"},
        )
        th = ensure_thread(user_id)
        return {"thread": th, "user_message": user_msg, "assistant_message": asst_msg}

    try:
        reply = await generate_assistant_chat_reply(
            user_message=body.content.strip(),
            summary=summary,
            history=history,
            user_id=user_id,
            score_id=body.score_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    asst_msg = append_message(
        user_id,
        "assistant",
        reply,
        meta={"source": "chat"},
    )
    th = ensure_thread(user_id)
    return {"thread": th, "user_message": user_msg, "assistant_message": asst_msg}
