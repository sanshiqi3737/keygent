"""
PyInstaller 打包入口：冻结后无需系统 Python，双击由 Electron 拉起本进程即可。

开发时不要用此文件日常启动，请继续用：py -m uvicorn backend.app:app --port 8000
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap() -> None:
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
        os.chdir(root)
        # 若同目录有 ffmpeg.exe，便于 librosa/audioread 解码 MP3
        os.environ["PATH"] = str(root) + os.pathsep + os.environ.get("PATH", "")


def main() -> None:
    _bootstrap()
    import uvicorn

    port = int(os.environ.get("PIANO_TUTOR_PORT", "8765"))
    app_mode = (os.environ.get("PIANO_APP_MODE") or "all").strip().lower()
    app_ref = {
        "all": "backend.app:app",
        "public": "backend.app:public_app",
        "admin": "backend.app:admin_app",
    }.get(app_mode, "backend.app:app")
    uvicorn.run(
        app_ref,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
