"""
账号认证逻辑（密码哈希、令牌签发与校验）。
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from .auth_store import (
    create_token,
    create_user,
    get_token_record,
    get_user_by_account,
    get_user_by_id,
    revoke_token,
    touch_last_login,
)

TOKEN_TTL_HOURS = 24 * 14  # 14 days
PBKDF2_ROUNDS = 260_000


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _normalize_account(account: str) -> str:
    return account.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt}${dk.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        alg, rounds_s, salt, hex_digest = encoded.split("$", 3)
        if alg != "pbkdf2_sha256":
            return False
        rounds = int(rounds_s)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), rounds).hex()
    return hmac.compare_digest(actual, hex_digest)


def register_user(account: str, password: str) -> Dict[str, Any]:
    acc = _normalize_account(account)
    if not acc:
        raise ValueError("账号不能为空")
    if len(password) < 6:
        raise ValueError("密码至少 6 位")
    if get_user_by_account(acc):
        raise RuntimeError("该账号已存在")
    try:
        return create_user(acc, hash_password(password))
    except Exception as e:
        raise RuntimeError("该账号已存在") from e


def issue_access_token(user_id: str) -> Dict[str, Any]:
    token = "pt_" + secrets.token_urlsafe(40)
    exp = _utc_now() + timedelta(hours=TOKEN_TTL_HOURS)
    create_token(token, user_id, _to_iso(exp))
    return {"access_token": token, "token_type": "bearer", "expires_at": _to_iso(exp)}


def login_user(account: str, password: str) -> Dict[str, Any]:
    acc = _normalize_account(account)
    u = get_user_by_account(acc)
    if not u or not verify_password(password, str(u.get("password_hash") or "")):
        raise PermissionError("账号或密码错误")
    touch_last_login(str(u["id"]))
    user = get_user_by_id(str(u["id"]))
    if not user:
        raise RuntimeError("用户不存在")
    token = issue_access_token(str(u["id"]))
    return {"user": user, **token}


def logout_token(token: str) -> None:
    revoke_token(token)


def get_current_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    rec = get_token_record(token)
    if not rec:
        return None
    if rec.get("revoked_at"):
        return None
    try:
        exp = _parse_iso(str(rec["expires_at"]))
    except Exception:
        return None
    if exp <= _utc_now():
        return None
    return get_user_by_id(str(rec["user_id"]))

