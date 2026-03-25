"""智能练习建议（阿里云百炼 / DashScope）。密钥来自环境变量；Beta 可由发布者通过 publisher-bundled.env 预置，勿把真实 Key 提交仓库。"""

from __future__ import annotations

import os

from .runtime_config_store import get_runtime_config


def get_dashscope_api_key() -> str:
    """百炼 API-Key，控制台创建。支持 DASHSCOPE_API_KEY 或兼容 BAILIAN_API_KEY。"""
    return (os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("BAILIAN_API_KEY") or "").strip()


def get_assistant_model() -> str:
    """通义模型名，如 qwen-turbo、qwen-plus、qwen-max。"""
    runtime_override = get_runtime_config("assistant_model")
    if runtime_override:
        return runtime_override.strip()
    return (os.environ.get("DASHSCOPE_MODEL") or "qwen-turbo").strip()


# OpenAI 兼容模式（北京地域）；若需新加坡等见百炼文档切换 base
DASHSCOPE_COMPAT_BASE = (
    os.environ.get("DASHSCOPE_COMPAT_BASE") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
).rstrip("/")
