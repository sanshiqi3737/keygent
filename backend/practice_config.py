"""练习/智能体相关 API 开关，与核心比对解耦。"""

from __future__ import annotations

import os


def is_practice_api_enabled() -> bool:
    """环境变量 ENABLE_PRACTICE_API，默认开启；设为 0/false/off 时关闭练习记录 API。"""
    v = (os.environ.get("ENABLE_PRACTICE_API") or "true").strip().lower()
    return v not in ("0", "false", "no", "off", "disabled")
