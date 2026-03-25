"""
曲目入库评估（v1）：
- 规则层：基于 MusicXML 抽取特征，产出 difficulty + abilities
- 可选 LLM 层：在规则结果基础上微调（受白名单约束）
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .assistant_config import DASHSCOPE_COMPAT_BASE, get_assistant_model, get_dashscope_api_key
from .audio_processing.musicxml_parser import parse_musicxml_techniques, parse_musicxml_to_notes

DIFFICULTIES = {"very_easy", "easy", "medium", "hard", "very_hard"}


def is_upload_llm_assessment_enabled() -> bool:
    """云端上传若觉得慢，可在 .env 设 PIANO_UPLOAD_ASSESSMENT_LLM=false 跳过百炼微调（仍保留规则评估）。"""
    v = os.environ.get("PIANO_UPLOAD_ASSESSMENT_LLM", "true").strip().lower()
    return v not in ("0", "false", "no", "off")
ABILITY_WHITELIST = {
    "pitch_accuracy",
    "slow_practice_control",
    "rhythm_stability",
    "tempo_control",
    "left_hand_control",
    "two_hand_coordination",
    "chord_balance",
    "articulation_control",
    "phrase_connection",
}


def _clamp_abilities(items: Any) -> List[str]:
    if not isinstance(items, list):
        return []
    out: List[str] = []
    for x in items:
        if isinstance(x, str):
            v = x.strip()
            if v in ABILITY_WHITELIST and v not in out:
                out.append(v)
    return out[:6]


def _estimate_polyphony_ratio(notes: List[Any], win_s: float = 0.03) -> float:
    if not notes:
        return 0.0
    starts = sorted(float(getattr(n, "start", 0.0) or 0.0) for n in notes)
    groups = 0
    poly_groups = 0
    i = 0
    n = len(starts)
    while i < n:
        j = i + 1
        while j < n and (starts[j] - starts[i]) <= win_s:
            j += 1
        groups += 1
        if (j - i) >= 2:
            poly_groups += 1
        i = j
    return round(poly_groups / max(1, groups), 4)


def _rule_assess(musicxml_path: str, title_hint: Optional[str] = None) -> Dict[str, Any]:
    notes, info = parse_musicxml_to_notes(musicxml_path)
    counts, _events = parse_musicxml_techniques(musicxml_path)
    note_count = len(notes)
    total_measures = int(getattr(info, "total_measures", 1) or 1)
    bpm = float(getattr(info, "bpm", 120.0) or 120.0)
    dur_s = max((float(getattr(n, "end", 0.0) or 0.0) for n in notes), default=0.0)
    density = round(note_count / max(1, total_measures), 3)
    poly_ratio = _estimate_polyphony_ratio(notes)
    pitches = [int(getattr(n, "pitch", 60) or 60) for n in notes]
    pitch_span = (max(pitches) - min(pitches)) if pitches else 0

    score = 0.0
    score += min(2.0, density / 2.8)
    score += min(1.6, max(0.0, bpm - 80.0) / 38.0)
    score += min(1.2, poly_ratio * 3.0)
    score += min(1.0, pitch_span / 20.0)
    if counts.get("Staccato", 0) + counts.get("Tenuto", 0) + counts.get("Accent", 0) >= 8:
        score += 0.5
    if total_measures >= 60:
        score += 0.4

    if score < 1.8:
        difficulty = "very_easy"
    elif score < 2.7:
        difficulty = "easy"
    elif score < 3.8:
        difficulty = "medium"
    elif score < 4.8:
        difficulty = "hard"
    else:
        difficulty = "very_hard"

    abilities: List[str] = []
    if density >= 3.0:
        abilities.append("pitch_accuracy")
    if bpm >= 105:
        abilities.append("tempo_control")
    if poly_ratio >= 0.18:
        abilities.extend(["two_hand_coordination", "chord_balance"])
    if counts.get("Staccato", 0) + counts.get("Tenuto", 0) + counts.get("Accent", 0) >= 6:
        abilities.append("articulation_control")
    if counts.get("Crescendo", 0) + counts.get("Diminuendo", 0) + counts.get("Decrescendo", 0) >= 2:
        abilities.append("phrase_connection")
    if "tempo_control" in abilities:
        abilities.append("rhythm_stability")
    if not abilities:
        abilities = ["slow_practice_control", "pitch_accuracy"]
    # keep order & clamp
    dedup = []
    seen = set()
    for a in abilities:
        if a in ABILITY_WHITELIST and a not in seen:
            seen.add(a)
            dedup.append(a)

    title = title_hint or Path(musicxml_path).stem
    return {
        "title": title,
        "difficulty": difficulty,
        "abilities": dedup[:6],
        "method": "rule",
        "features": {
            "note_count": note_count,
            "total_measures": total_measures,
            "bpm": round(bpm, 2),
            "duration_s": round(dur_s, 2),
            "density_notes_per_measure": density,
            "polyphony_ratio": poly_ratio,
            "pitch_span_semitones": pitch_span,
            "technique_counts": counts,
            "difficulty_score": round(score, 3),
        },
        "reason": "基于音符密度、速度、复调比例、音域跨度与技巧标记的规则评估。",
    }


def _llm_prompt(rule_meta: Dict[str, Any]) -> str:
    payload = json.dumps(rule_meta, ensure_ascii=False, indent=2)
    return (
        "请基于以下规则评估结果，给出更稳妥的教学标签。"
        "必须只返回 JSON，不要额外文字。"
        "字段：difficulty(very_easy/easy/medium/hard/very_hard),"
        "abilities(从白名单中选), reason(<=80字)。\n\n"
        f"{payload}\n\n"
        f"abilities 白名单：{sorted(ABILITY_WHITELIST)}"
    )


async def _refine_with_llm(rule_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    api_key = get_dashscope_api_key()
    if not api_key:
        return None
    url = f"{DASHSCOPE_COMPAT_BASE}/chat/completions"
    body = {
        "model": get_assistant_model(),
        "messages": [
            {"role": "system", "content": "你是乐谱分级助手。严格输出 JSON。"},
            {"role": "user", "content": _llm_prompt(rule_meta)},
        ],
        "temperature": 0.2,
        "max_tokens": 300,
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
        if resp.status_code != 200:
            return None
        raw = str(resp.json()["choices"][0]["message"]["content"]).strip()
        s = raw.find("{")
        e = raw.rfind("}")
        if s < 0 or e <= s:
            return None
        obj = json.loads(raw[s : e + 1])
        if not isinstance(obj, dict):
            return None
        diff = obj.get("difficulty")
        abilities = _clamp_abilities(obj.get("abilities"))
        if not isinstance(diff, str) or diff not in DIFFICULTIES:
            return None
        reason = obj.get("reason")
        return {
            "difficulty": diff,
            "abilities": abilities or rule_meta.get("abilities", []),
            "reason": str(reason).strip()[:160] if isinstance(reason, str) else "LLM 调整",
        }
    except Exception:
        return None


def _meta_path(score_dir: Path) -> Path:
    return score_dir / "meta.json"


def load_score_meta(score_dir: Path) -> Optional[Dict[str, Any]]:
    p = _meta_path(score_dir)
    if not p.exists():
        return None
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def save_score_meta(score_dir: Path, meta: Dict[str, Any]) -> None:
    score_dir.mkdir(parents=True, exist_ok=True)
    _meta_path(score_dir).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def assess_and_save_score_meta(
    score_dir: Path,
    musicxml_path: Path,
    *,
    title_hint: Optional[str] = None,
    enable_llm: bool = True,
) -> Dict[str, Any]:
    rule_meta = _rule_assess(str(musicxml_path), title_hint=title_hint)
    final_meta = {
        "title": rule_meta.get("title"),
        "difficulty": rule_meta.get("difficulty"),
        "abilities": rule_meta.get("abilities"),
        "assessment": {
            "method": "rule",
            "reason": rule_meta.get("reason"),
            "features": rule_meta.get("features"),
        },
    }
    if enable_llm and not is_upload_llm_assessment_enabled():
        enable_llm = False
    if enable_llm:
        llm = await _refine_with_llm(rule_meta)
        if llm:
            final_meta["difficulty"] = llm["difficulty"]
            final_meta["abilities"] = llm["abilities"]
            final_meta["assessment"] = {
                "method": "rule+llm",
                "reason": llm["reason"],
                "features": rule_meta.get("features"),
                "rule_baseline": {
                    "difficulty": rule_meta.get("difficulty"),
                    "abilities": rule_meta.get("abilities"),
                },
            }
    save_score_meta(score_dir, final_meta)
    return final_meta

