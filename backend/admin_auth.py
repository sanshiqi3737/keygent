"""
开发者管理端轻量鉴权（Beta）：
- 口令换取临时 token
- token 仅用于管理接口访问
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import os

_TOKENS: Dict[str, datetime] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_admin_passcode() -> str:
    return (os.environ.get("ADMIN_PASSCODE") or "").strip()


def verify_passcode(passcode: str) -> bool:
    conf = get_admin_passcode()
    return bool(conf) and passcode == conf


def issue_admin_token(ttl_minutes: int = 180) -> str:
    token = secrets.token_urlsafe(32)
    _TOKENS[token] = _utc_now() + timedelta(minutes=max(10, ttl_minutes))
    return token


def verify_admin_token(token: Optional[str]) -> bool:
    if not token:
        return False
    exp = _TOKENS.get(token)
    if not exp:
        return False
    if exp < _utc_now():
        _TOKENS.pop(token, None)
        return False
    return True

