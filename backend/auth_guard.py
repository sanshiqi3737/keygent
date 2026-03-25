from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from .auth_service import get_current_user_by_token


def extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录：缺少 Authorization")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="未登录：Authorization 格式错误")
    token = authorization[len(prefix):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="未登录：Token 为空")
    return token


def require_login_user_id(authorization: Optional[str]) -> str:
    token = extract_bearer_token(authorization)
    user = get_current_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    uid = str(user.get("id") or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="登录信息异常，请重新登录")
    return uid

