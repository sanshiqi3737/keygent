from __future__ import annotations

import sys

from dotenv import load_dotenv
from fastapi import FastAPI

from .paths import project_root

# 环境变量加载顺序（后者覆盖前者同名变量）：
# - 冻结：publisher-bundled.env（发布者打包注入）→ resources/piano/.env → piano-backend/.env
# - 开发：desktop/publisher.env（可选，与打包同源）→ 仓库根 .env
_PROJECT_ROOT = project_root()
if getattr(sys, "frozen", False):
    load_dotenv(_PROJECT_ROOT.parent / "publisher-bundled.env")
    load_dotenv(_PROJECT_ROOT.parent / ".env")
    load_dotenv(_PROJECT_ROOT / ".env", override=True)
else:
    _publisher_env = _PROJECT_ROOT / "desktop" / "publisher.env"
    if _publisher_env.is_file():
        load_dotenv(_publisher_env)
    load_dotenv(_PROJECT_ROOT / ".env", override=True)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes.assistant import router as assistant_router
from .routes.admin import router as admin_router
from .routes.auth import router as auth_router
from .routes.compare import router as compare_router
from .routes.practice import router as practice_router
from .routes.score import router as score_router

_FRONTEND_DIST = _PROJECT_ROOT / "frontend" / "dist"


def _apply_cors(app: FastAPI) -> None:
    # 不能同时使用 allow_origins=["*"] 与 allow_credentials=True（浏览器会拒绝带 Authorization 的跨域请求）。
    # JWT 放在 Authorization 头、不用 Cookie 时，关闭 credentials 即可用通配 origin。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_public_app(*, include_admin_routes: bool = False, mount_spa: bool = True) -> FastAPI:
    app = FastAPI(title="Piano Tutor Public API", version="0.1.0")
    _apply_cors(app)

    app.include_router(compare_router)
    app.include_router(score_router)
    app.include_router(practice_router)
    app.include_router(assistant_router)
    app.include_router(auth_router)
    if include_admin_routes:
        app.include_router(admin_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    # Beta / 生产一体：存在 frontend/dist 时由同一端口提供静态页面（与 /api 同源）
    if mount_spa and _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").exists():
        app.mount(
            "/",
            StaticFiles(directory=str(_FRONTEND_DIST), html=True),
            name="spa",
        )

    return app


def create_admin_app() -> FastAPI:
    app = FastAPI(title="Piano Tutor Admin API", version="0.1.0")
    _apply_cors(app)
    app.include_router(admin_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "scope": "admin"}

    return app


# 兼容旧入口：当前仍保留全功能单端口模式
app = create_public_app(include_admin_routes=True, mount_spa=True)

# 新入口：为发布准备的用户/开发者分离部署
public_app = create_public_app(include_admin_routes=False, mount_spa=True)
admin_app = create_admin_app()

