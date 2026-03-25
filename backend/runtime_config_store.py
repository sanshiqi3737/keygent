"""
运行时配置（可由管理端动态调整，不必重发版本）。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Dict, Optional

from .paths import practice_data_dir


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _connect() -> sqlite3.Connection:
    root = practice_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(root / "runtime_config.db"))
    conn.row_factory = sqlite3.Row
    return conn


def init_runtime_config_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_configs (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def get_runtime_config(key: str) -> Optional[str]:
    init_runtime_config_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM runtime_configs WHERE key = ?",
            (key,),
        ).fetchone()
    if not row:
        return None
    v = str(row["value"] or "").strip()
    return v or None


def set_runtime_config(key: str, value: str) -> None:
    init_runtime_config_db()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_configs(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, _utc_now_iso()),
        )
        conn.commit()


def list_runtime_configs() -> Dict[str, str]:
    init_runtime_config_db()
    with _connect() as conn:
        rows = conn.execute("SELECT key, value FROM runtime_configs").fetchall()
    out: Dict[str, str] = {}
    for r in rows:
        k = str(r["key"] or "").strip()
        if not k:
            continue
        out[k] = str(r["value"] or "")
    return out

