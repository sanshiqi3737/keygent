"""
调用阿里云百炼（DashScope OpenAI 兼容接口）生成练习建议。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from .assistant_config import DASHSCOPE_COMPAT_BASE, get_assistant_model, get_dashscope_api_key

SYSTEM_PROMPT = """你是钢琴练习助手，只根据用户提供的「练习数据 JSON」给建议。

规则：
1. 用简体中文，语气友好、具体、可执行（练哪几小节、注意什么、可配合节拍器慢练等）。
2. 数据来自自动检测，可能有误差；不要声称「绝对正确」，不要说「系统已诊断出疾病」类话术。
3. 不要编造数据里没有的小节号、准确率或技巧。
4. 控制在 400 字以内，分点列出更佳。
5. 若数据里几乎没有练习记录，说明需要先完成几次带保存的练习，再给简短鼓励即可。
6. 若 latest_session_meta.compare_mode=beginner_pitch_only，重点给音准与慢练建议，不要用节奏分做强结论。
7. 若 latest_session_meta.compare_mode=advanced_rhythm，可结合节奏稳定性给出节拍器/分段节奏建议。
"""


def _build_user_payload(
    summary: Dict[str, Any],
    latest_errors_sample: List[Dict[str, Any]],
    score_id: Optional[str],
    latest_session_meta: Optional[Dict[str, Any]] = None,
) -> str:
    payload = {
        "practice_summary": summary,
        "latest_session_errors_sample": latest_errors_sample[:25],
        "filter_score_id": score_id,
        "latest_session_meta": latest_session_meta or {},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


async def generate_practice_suggestion(
    summary: Dict[str, Any],
    latest_errors_sample: List[Dict[str, Any]],
    *,
    score_id: Optional[str] = None,
    latest_session_meta: Optional[Dict[str, Any]] = None,
) -> str:
    api_key = get_dashscope_api_key()
    if not api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY")

    model = get_assistant_model()
    url = f"{DASHSCOPE_COMPAT_BASE}/chat/completions"
    user_content = _build_user_payload(
        summary, latest_errors_sample, score_id, latest_session_meta=latest_session_meta
    )

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请根据以下练习数据给出今日练习建议：\n\n{user_content}"},
        ],
        "temperature": 0.5,
        "max_tokens": 1024,
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )

    if resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text[:500]
        raise RuntimeError(f"DashScope HTTP {resp.status_code}: {detail}")

    data = resp.json()
    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"DashScope 响应格式异常: {data!r}") from e


async def generate_assistant_chat_reply(
    *,
    user_message: str,
    summary: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None,
    user_id: Optional[str] = None,
    score_id: Optional[str] = None,
) -> str:
    """
    会话式回复（每用户长期线程）。history 仅需 role/content 字段。
    """
    api_key = get_dashscope_api_key()
    if not api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY")
    model = get_assistant_model()
    url = f"{DASHSCOPE_COMPAT_BASE}/chat/completions"
    summary_payload = {
        "user_id": user_id,
        "score_id": score_id,
        "practice_summary": summary or {},
    }
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                SYSTEM_PROMPT
                + "\n你处在多轮会话模式：请结合 history 与 summary，回复简洁、可执行。"
            ),
        },
        {
            "role": "system",
            "content": "summary_json:\n" + json.dumps(summary_payload, ensure_ascii=False),
        },
    ]
    for h in (history or [])[-12:]:
        role = str(h.get("role") or "")
        content = str(h.get("content") or "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 1024,
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
    if resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text[:500]
        raise RuntimeError(f"DashScope HTTP {resp.status_code}: {detail}")
    data = resp.json()
    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"DashScope 响应格式异常: {data!r}") from e
