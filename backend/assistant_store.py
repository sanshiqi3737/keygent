"""
助手会话持久化（按用户隔离，单长期线程）。
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .paths import practice_data_dir


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _connect() -> sqlite3.Connection:
    root = practice_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(root / "assistant.db"))
    conn.row_factory = sqlite3.Row
    return conn


def init_assistant_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_threads (
                thread_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_messages (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                meta_json TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_assistant_messages_thread_time ON assistant_messages(thread_id, created_at ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_assistant_messages_user_time ON assistant_messages(user_id, created_at DESC)"
        )
        conn.commit()


def ensure_thread(user_id: str) -> Dict[str, Any]:
    init_assistant_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT thread_id, user_id, created_at, updated_at FROM assistant_threads WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            return {
                "thread_id": row["thread_id"],
                "user_id": row["user_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        now = _utc_now_iso()
        tid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO assistant_threads(thread_id, user_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (tid, user_id, now, now),
        )
        conn.commit()
        return {"thread_id": tid, "user_id": user_id, "created_at": now, "updated_at": now}


def append_message(
    user_id: str,
    role: str,
    content: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    th = ensure_thread(user_id)
    msg_id = str(uuid.uuid4())
    now = _utc_now_iso()
    meta_s = json.dumps(meta, ensure_ascii=False) if meta else None
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO assistant_messages(id, thread_id, user_id, role, content, created_at, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (msg_id, th["thread_id"], user_id, role, content, now, meta_s),
        )
        conn.execute(
            "UPDATE assistant_threads SET updated_at = ? WHERE thread_id = ?",
            (now, th["thread_id"]),
        )
        conn.commit()
    return {
        "id": msg_id,
        "thread_id": th["thread_id"],
        "user_id": user_id,
        "role": role,
        "content": content,
        "created_at": now,
        "meta": meta,
    }


def list_messages(user_id: str, *, limit: int = 50) -> List[Dict[str, Any]]:
    th = ensure_thread(user_id)
    limit = max(1, min(limit, 200))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, thread_id, user_id, role, content, created_at, meta_json
            FROM assistant_messages
            WHERE thread_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (th["thread_id"], limit),
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "thread_id": r["thread_id"],
                "user_id": r["user_id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
                "meta": json.loads(r["meta_json"]) if r["meta_json"] else None,
            }
        )
    return out

