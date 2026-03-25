"""
账号与访问令牌持久化（SQLite）。
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .paths import practice_data_dir


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _connect() -> sqlite3.Connection:
    root = practice_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(root / "auth.db"))
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                account TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_auth_tokens_user ON auth_tokens(user_id, created_at DESC)"
        )
        conn.commit()


def get_user_by_account(account: str) -> Optional[Dict[str, Any]]:
    init_auth_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, account, password_hash, created_at, updated_at, last_login_at FROM users WHERE account = ?",
            (account,),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    init_auth_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, account, created_at, updated_at, last_login_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def create_user(account: str, password_hash: str) -> Dict[str, Any]:
    init_auth_db()
    now = _utc_now_iso()
    uid = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users (id, account, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (uid, account, password_hash, now, now),
        )
        conn.commit()
    out = get_user_by_id(uid)
    if not out:
        raise RuntimeError("创建用户失败")
    return out


def touch_last_login(user_id: str) -> None:
    init_auth_db()
    now = _utc_now_iso()
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (now, now, user_id),
        )
        conn.commit()


def create_token(token: str, user_id: str, expires_at: str) -> None:
    init_auth_db()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO auth_tokens (token, user_id, created_at, expires_at, revoked_at)
            VALUES (?, ?, ?, ?, NULL)
            """,
            (token, user_id, _utc_now_iso(), expires_at),
        )
        conn.commit()


def revoke_token(token: str) -> None:
    init_auth_db()
    with _connect() as conn:
        conn.execute(
            "UPDATE auth_tokens SET revoked_at = ? WHERE token = ? AND revoked_at IS NULL",
            (_utc_now_iso(), token),
        )
        conn.commit()


def get_token_record(token: str) -> Optional[Dict[str, Any]]:
    init_auth_db()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT token, user_id, created_at, expires_at, revoked_at
            FROM auth_tokens
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
    return dict(row) if row else None

