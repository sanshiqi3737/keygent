"""
项目根目录解析：开发时 = 仓库根（含 backend/、frontend/）；PyInstaller 冻结后 = exe 所在目录。
"""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """数据目录、frontend/dist、.env 均相对此根路径。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # 开发：本文件在 backend/paths.py → 上一级为仓库根
    return Path(__file__).resolve().parent.parent


def scores_data_dir() -> Path:
    return project_root() / "data" / "scores"


def practice_data_dir() -> Path:
    return project_root() / "data" / "practice"
