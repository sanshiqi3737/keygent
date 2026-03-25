from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ..admin_auth import issue_admin_token, verify_admin_token, verify_passcode
from ..practice_store import compute_summary, init_db, list_user_ids
from ..runtime_config_store import get_runtime_config, set_runtime_config

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminAuthRequest(BaseModel):
    passcode: str = Field(..., min_length=1, max_length=256)


class AdminRuntimeConfigUpdateRequest(BaseModel):
    assistant_model: str = Field(..., min_length=1, max_length=128, description="如 qwen-turbo / qwen-plus")


def _require_admin(x_admin_token: str | None) -> None:
    if not verify_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="管理员鉴权失败")


@router.post("/auth")
async def admin_auth(body: AdminAuthRequest) -> Dict[str, Any]:
    if not verify_passcode(body.passcode.strip()):
        raise HTTPException(status_code=403, detail="管理口令错误")
    token = issue_admin_token()
    return {"token": token, "expires_in_minutes": 180}


@router.get("/users-overview")
async def admin_users_overview(
    limit: int = Query(50, ge=1, le=200),
    x_admin_token: str | None = Header(default=None),
) -> Dict[str, Any]:
    _require_admin(x_admin_token)
    init_db()
    users = list_user_ids(limit=limit)
    rows: List[Dict[str, Any]] = []
    for uid in users:
        s = compute_summary(uid, score_id=None, last_n=30)
        rows.append(
            {
                "user_id": uid,
                "sessions": int(s.get("window_sessions") or 0),
                "accuracy_mean": (s.get("accuracy") or {}).get("mean"),
                "latest_session_at": s.get("latest_session_at"),
            }
        )
    return {"count": len(rows), "rows": rows}


@router.get("/runtime-config")
async def admin_runtime_config(
    x_admin_token: str | None = Header(default=None),
) -> Dict[str, Any]:
    _require_admin(x_admin_token)
    return {
        "assistant_model": get_runtime_config("assistant_model") or "",
    }


@router.put("/runtime-config")
async def admin_runtime_config_update(
    body: AdminRuntimeConfigUpdateRequest,
    x_admin_token: str | None = Header(default=None),
) -> Dict[str, Any]:
    _require_admin(x_admin_token)
    model = body.assistant_model.strip()
    if not model:
        raise HTTPException(status_code=400, detail="assistant_model 不能为空")
    set_runtime_config("assistant_model", model)
    return {"ok": True, "assistant_model": model}

