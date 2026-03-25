from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..auth_service import (
    get_current_user_by_token,
    login_user,
    logout_token,
    register_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRegisterRequest(BaseModel):
    account: str = Field(..., min_length=3, max_length=128, description="登录账号（建议邮箱）")
    password: str = Field(..., min_length=6, max_length=128)


class AuthLoginRequest(BaseModel):
    account: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=1, max_length=128)


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Authorization 格式错误")
    token = authorization[len(prefix):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token 为空")
    return token


@router.post("/register")
async def auth_register(body: AuthRegisterRequest) -> Dict[str, Any]:
    try:
        user = register_user(body.account, body.password)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"user": user}


@router.post("/login")
async def auth_login(body: AuthLoginRequest) -> Dict[str, Any]:
    try:
        return login_user(body.account, body.password)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/me")
async def auth_me(authorization: str | None = Header(default=None)) -> Dict[str, Any]:
    token = _extract_bearer(authorization)
    user = get_current_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return {"user": user}


@router.post("/logout")
async def auth_logout(authorization: str | None = Header(default=None)) -> Dict[str, Any]:
    token = _extract_bearer(authorization)
    logout_token(token)
    return {"ok": True}

