"""
练习会话持久化（SQLite）。供成长轨迹、未来智能体决策等使用。
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

from .paths import practice_data_dir


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_int(value: Any, default: int = 0) -> int:
    """容错转换：None/非法值按 default 处理，避免写库时报 500。"""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _connect() -> sqlite3.Connection:
    root = practice_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(root / "practice.db"))
    conn.row_factory = sqlite3.Row
    return conn


def _audio_root() -> Path:
    root = practice_data_dir() / "audios"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [str(row[1]) for row in cur.fetchall()]


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if column in _table_columns(conn, table):
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS practice_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                score_id TEXT,
                created_at TEXT NOT NULL,
                ref_note_count INTEGER NOT NULL,
                played_note_count INTEGER NOT NULL,
                accuracy REAL NOT NULL,
                error_count INTEGER NOT NULL,
                metrics_json TEXT NOT NULL,
                errors_json TEXT NOT NULL,
                extra_json TEXT
            )
            """
        )
        # 旧库可能缺列，仅 CREATE IF NOT EXISTS 不会补全
        _ensure_column(conn, "practice_sessions", "extra_json", "extra_json TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_practice_user_time ON practice_sessions(user_id, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_practice_score_time ON practice_sessions(score_id, created_at DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS practice_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                score_id TEXT,
                session_id TEXT,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_practice_events_user_time ON practice_events(user_id, created_at DESC)"
        )
        conn.commit()


def insert_session(
    user_id: str,
    metrics: Dict[str, Any],
    errors: List[Dict[str, Any]],
    *,
    score_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """
    写入一条练习记录。metrics 建议为 build_practice_metrics 的返回值。
    返回 session id。
    """
    init_db()
    sid = str(uuid.uuid4())
    pitch = metrics.get("pitch") or {}
    nc = metrics.get("note_counts") or {}
    acc = float(pitch.get("accuracy", 0.0))
    err_total = _to_int(pitch.get("error_total", len(errors)), len(errors))
    payload_extra = json.dumps(extra, ensure_ascii=False) if extra else None
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO practice_sessions (
                id, user_id, score_id, created_at,
                ref_note_count, played_note_count, accuracy, error_count,
                metrics_json, errors_json, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sid,
                user_id,
                score_id,
                _utc_now_iso(),
                _to_int(nc.get("reference", 0), 0),
                _to_int(nc.get("played", 0), 0),
                acc,
                err_total,
                json.dumps(metrics, ensure_ascii=False),
                json.dumps(errors, ensure_ascii=False),
                payload_extra,
            ),
        )
        conn.commit()
    return sid


def list_sessions(
    user_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    score_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    init_db()
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    with _connect() as conn:
        if score_id:
            rows = conn.execute(
                """
                SELECT id, user_id, score_id, created_at, ref_note_count, played_note_count,
                       accuracy, error_count, metrics_json, extra_json
                FROM practice_sessions
                WHERE user_id = ? AND score_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, score_id, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, user_id, score_id, created_at, ref_note_count, played_note_count,
                       accuracy, error_count, metrics_json, extra_json
                FROM practice_sessions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            ).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        m = json.loads(r["metrics_json"])
        extra_obj: Dict[str, Any] = {}
        try:
            extra_obj = json.loads(r["extra_json"]) if r["extra_json"] else {}
        except (TypeError, json.JSONDecodeError):
            extra_obj = {}
        out.append(
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "score_id": r["score_id"],
                "created_at": r["created_at"],
                "ref_note_count": r["ref_note_count"],
                "played_note_count": r["played_note_count"],
                "accuracy": r["accuracy"],
                "error_count": r["error_count"],
                "metrics": m,
                "extra": extra_obj,
                "has_practice_audio": bool(extra_obj.get("practice_audio_relpath")),
                "practice_audio_deleted": bool(extra_obj.get("practice_audio_deleted")),
            }
        )
    return out


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with _connect() as conn:
        r = conn.execute(
            "SELECT * FROM practice_sessions WHERE id = ?", (session_id,)
        ).fetchone()
    if not r:
        return None
    return {
        "id": r["id"],
        "user_id": r["user_id"],
        "score_id": r["score_id"],
        "created_at": r["created_at"],
        "ref_note_count": r["ref_note_count"],
        "played_note_count": r["played_note_count"],
        "accuracy": r["accuracy"],
        "error_count": r["error_count"],
        "metrics": json.loads(r["metrics_json"]),
        "errors": json.loads(r["errors_json"]),
        "extra": json.loads(r["extra_json"]) if r["extra_json"] else None,
    }


def update_session_extra(session_id: str, extra: Dict[str, Any]) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            "UPDATE practice_sessions SET extra_json = ? WHERE id = ?",
            (json.dumps(extra, ensure_ascii=False), session_id),
        )
        conn.commit()


def store_practice_audio_blob(
    user_id: str,
    audio_bytes: bytes,
    *,
    suffix: str = ".wav",
) -> Dict[str, Any]:
    """
    保存练习原始音频到 data/practice/audios，返回可写入 session.extra 的元信息。
    """
    aid = str(uuid.uuid4())
    suf = str(suffix or ".wav").lower()
    if not suf.startswith("."):
        suf = "." + suf
    relpath = f"audios/{aid}{suf}"
    out_path = practice_data_dir() / relpath
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio_bytes)
    return {
        "practice_audio_id": aid,
        "practice_audio_relpath": relpath,
        "practice_audio_size": int(len(audio_bytes)),
        "practice_audio_owner_user_id": user_id,
        "practice_audio_deleted": False,
        "practice_audio_deleted_at": None,
    }


def compute_summary(
    user_id: str,
    *,
    score_id: Optional[str] = None,
    last_n: int = 30,
) -> Dict[str, Any]:
    """
    对最近 last_n 条练习会话做聚合（用于测试与趋势观察）。
    """
    init_db()
    last_n = max(1, min(last_n, 200))
    with _connect() as conn:
        if score_id:
            rows = conn.execute(
                """
                SELECT accuracy, error_count, metrics_json, extra_json, created_at
                FROM practice_sessions
                WHERE user_id = ? AND score_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, score_id, last_n),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT accuracy, error_count, metrics_json, extra_json, created_at
                FROM practice_sessions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, last_n),
            ).fetchall()

    if not rows:
        return {
            "user_id": user_id,
            "score_id": score_id,
            "window_sessions": 0,
            "last_n_requested": last_n,
            "accuracy": None,
            "errors": None,
            "rhythm": None,
            "weak_measures_top": [],
            "stability_across_sessions": {
                "accuracy_std": None,
                "accuracy_range": None,
                "rhythm_score_std": None,
                "composite_stability_mean": None,
                "sessions_with_composite": 0,
                "note": "至少 2 条会话时可计算准确率波动；节奏标准差需多条含 rhythm.score。",
            },
            "latest_session_at": None,
        }

    accs: List[float] = []
    err_counts: List[int] = []
    for r in rows:
        try:
            accs.append(float(r["accuracy"]))
            err_counts.append(int(r["error_count"]))
        except (TypeError, ValueError, KeyError):
            accs.append(0.0)
            err_counts.append(0)
    rhythm_scores: List[float] = []
    rhythm_cv: List[float] = []
    composite_stability: List[float] = []
    weak_agg: Counter = Counter()
    compare_mode_counter: Counter = Counter()

    for r in rows:
        try:
            m = json.loads(r["metrics_json"])
        except json.JSONDecodeError:
            continue
        if not isinstance(m, dict):
            continue
        # 若用户为本次练习填写过仅练习小节范围，就只统计该范围内的薄弱小节
        extra_obj: Dict[str, Any] = {}
        try:
            extra_json = r["extra_json"]
            extra_obj = json.loads(extra_json) if extra_json else {}
        except (TypeError, json.JSONDecodeError):
            extra_obj = {}
        if not isinstance(extra_obj, dict):
            extra_obj = {}

        focus_start = None
        focus_end = None
        try:
            if extra_obj.get("focus_start_measure") is not None:
                focus_start = int(extra_obj["focus_start_measure"])
            if extra_obj.get("focus_end_measure") is not None:
                focus_end = int(extra_obj["focus_end_measure"])
        except (TypeError, ValueError):
            focus_start = None
            focus_end = None
        cm = extra_obj.get("compare_mode")
        if isinstance(cm, str) and cm:
            compare_mode_counter[cm] += 1

        rh_raw = m.get("rhythm")
        rh: Dict[str, Any] = rh_raw if isinstance(rh_raw, dict) else {}
        if rh.get("score") is not None:
            try:
                rhythm_scores.append(float(rh["score"]))
            except (TypeError, ValueError, KeyError):
                pass
        if rh.get("cv_onset") is not None:
            try:
                rhythm_cv.append(float(rh["cv_onset"]))
            except (TypeError, ValueError, KeyError):
                pass
        stab_raw = m.get("stability")
        stab: Dict[str, Any] = stab_raw if isinstance(stab_raw, dict) else {}
        cs = stab.get("composite_stability_score")
        if cs is not None:
            try:
                composite_stability.append(float(cs))
            except (TypeError, ValueError):
                pass
        wm_raw = m.get("weak_measures") or {}
        wm: Dict[str, Any] = wm_raw if isinstance(wm_raw, dict) else {}
        for meas, cnt in wm.items():
            try:
                meas_int = int(meas)
            except (TypeError, ValueError):
                continue
            if focus_start is not None and meas_int < focus_start:
                continue
            if focus_end is not None and meas_int > focus_end:
                continue
            weak_agg[str(meas_int)] += _to_int(cnt, 0)

    top_weak = [
        {"measure": k, "error_count": v}
        for k, v in sorted(weak_agg.items(), key=lambda x: -x[1])[:15]
    ]

    acc_std = round(pstdev(accs), 6) if len(accs) >= 2 else None
    acc_range = round(max(accs) - min(accs), 6) if len(accs) >= 1 else None
    rhy_std = round(pstdev(rhythm_scores), 4) if len(rhythm_scores) >= 2 else None
    comp_mean = round(mean(composite_stability), 4) if composite_stability else None

    return {
        "user_id": user_id,
        "score_id": score_id,
        "window_sessions": len(rows),
        "last_n_requested": last_n,
        "accuracy": {
            "latest": accs[0],
            "mean": round(mean(accs), 6),
            "min": round(min(accs), 6),
            "max": round(max(accs), 6),
        },
        "errors": {
            "latest_error_count": err_counts[0],
            "mean_error_count": round(mean(err_counts), 4),
        },
        "rhythm": {
            "sessions_with_rhythm_score": len(rhythm_scores),
            "score_mean": round(mean(rhythm_scores), 4) if rhythm_scores else None,
            "cv_onset_mean": round(mean(rhythm_cv), 4) if rhythm_cv else None,
        },
        "weak_measures_top": top_weak,
        "stability_across_sessions": {
            "accuracy_std": acc_std,
            "accuracy_range": acc_range,
            "rhythm_score_std": rhy_std,
            "composite_stability_mean": comp_mean,
            "sessions_with_composite": len(composite_stability),
            "note": "accuracy_std/range 反映多次练习发挥波动；不含力度。",
        },
        "compare_mode_distribution": {
            k: int(v) for k, v in sorted(compare_mode_counter.items(), key=lambda x: -x[1])
        },
        "latest_session_at": rows[0]["created_at"],
    }


def insert_event(
    user_id: str,
    event_type: str,
    *,
    score_id: Optional[str] = None,
    session_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> str:
    """记录一条用户/客户端事件（按钮、跳过片段等），与比对主流程解耦。"""
    init_db()
    eid = str(uuid.uuid4())
    payload_s = json.dumps(payload, ensure_ascii=False) if payload else None
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO practice_events (
                id, user_id, score_id, session_id, event_type, created_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eid,
                user_id,
                score_id,
                session_id,
                event_type.strip()[:128],
                _utc_now_iso(),
                payload_s,
            ),
        )
        conn.commit()
    return eid


def list_events(
    user_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    init_db()
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    with _connect() as conn:
        if event_type:
            rows = conn.execute(
                """
                SELECT id, user_id, score_id, session_id, event_type, created_at, payload_json
                FROM practice_events
                WHERE user_id = ? AND event_type = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, event_type, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, user_id, score_id, session_id, event_type, created_at, payload_json
                FROM practice_events
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            ).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "score_id": r["score_id"],
                "session_id": r["session_id"],
                "event_type": r["event_type"],
                "created_at": r["created_at"],
                "payload": json.loads(r["payload_json"]) if r["payload_json"] else None,
            }
        )
    return out


def list_user_ids(limit: int = 200) -> List[str]:
    """
    返回有练习数据的用户 ID 列表（按最近活跃时间倒序）。
    """
    init_db()
    limit = max(1, min(limit, 1000))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT user_id, MAX(created_at) AS last_at
            FROM practice_sessions
            GROUP BY user_id
            ORDER BY last_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [str(r["user_id"]) for r in rows if r["user_id"]]
