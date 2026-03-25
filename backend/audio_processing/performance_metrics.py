"""
练习表现结构化指标（供持久化与未来智能体使用）。

从参考音符、演奏音符与比对结果汇总多维度摘要。
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Optional, Union

from .alignment import combined_dtw_align, is_dtw_available
from .midi_parser import MidiNote

ErrorLike = Union[Dict[str, Any], Any]


def _count_error_types(errors: List[ErrorLike]) -> Dict[str, int]:
    c = Counter()
    for e in errors:
        d = e if isinstance(e, dict) else dict(e)
        t = str(d.get("type", "unknown"))
        c[t] += 1
    return {
        "wrong": int(c.get("wrong", 0)),
        "missed": int(c.get("missed", 0)),
        "extra": int(c.get("extra", 0)),
    }


def _errors_by_measure(errors: List[ErrorLike]) -> Dict[str, int]:
    c: Counter = Counter()
    for e in errors:
        d = e if isinstance(e, dict) else dict(e)
        m = d.get("measure")
        if m is not None:
            c[int(m)] += 1
    return {str(k): int(v) for k, v in sorted(c.items())}


def _pitch_error_ratios(err_counts: Dict[str, int], error_total: int) -> Dict[str, float]:
    if error_total <= 0:
        return {"wrong_ratio": 0.0, "missed_ratio": 0.0, "extra_ratio": 0.0}
    w, m, x = err_counts["wrong"], err_counts["missed"], err_counts["extra"]
    return {
        "wrong_ratio": round(w / error_total, 4),
        "missed_ratio": round(m / error_total, 4),
        "extra_ratio": round(x / error_total, 4),
    }


def compute_rhythm_summary(
    reference: List[MidiNote],
    played: List[MidiNote],
    pitch_tolerance_semitones: int = 1,
    ms_ref_bad_rhythm: float = 200.0,
) -> Dict[str, Any]:
    """
    基于 DTW 一对一匹配且音高一致（在容差内）的音符对，统计起音时间偏差。
    含客观波动指标：标准差、变异系数、P90（疲劳/不稳定时常升高）。
    """
    empty = {
        "available": False,
        "mean_abs_onset_ms": None,
        "median_abs_onset_ms": None,
        "std_abs_onset_ms": None,
        "cv_onset": None,
        "p90_abs_onset_ms": None,
        "score": None,
        "matched_timing_pairs": 0,
    }
    if not is_dtw_available() or not reference or not played:
        return empty

    matched_pairs, _, _, ref_sorted, play_sorted = combined_dtw_align(reference, played)
    deltas_ms: List[float] = []
    for i, j in matched_pairs:
        rn, pn = ref_sorted[i], play_sorted[j]
        if abs(rn.pitch - pn.pitch) <= pitch_tolerance_semitones:
            deltas_ms.append(abs(float(pn.start) - float(rn.start)) * 1000.0)

    if not deltas_ms:
        return {
            "available": True,
            "mean_abs_onset_ms": None,
            "median_abs_onset_ms": None,
            "std_abs_onset_ms": None,
            "cv_onset": None,
            "p90_abs_onset_ms": None,
            "score": None,
            "matched_timing_pairs": 0,
        }

    mean_abs = sum(deltas_ms) / len(deltas_ms)
    sorted_d = sorted(deltas_ms)
    mid = sorted_d[len(sorted_d) // 2]
    variance = sum((x - mean_abs) ** 2 for x in deltas_ms) / len(deltas_ms)
    std = math.sqrt(variance)
    cv = std / mean_abs if mean_abs > 1e-9 else None
    p90_idx = min(len(sorted_d) - 1, int(math.ceil(0.9 * len(sorted_d)) - 1))
    p90 = sorted_d[max(0, p90_idx)]
    score = max(0.0, min(1.0, 1.0 - mean_abs / max(ms_ref_bad_rhythm, 1e-6)))

    return {
        "available": True,
        "mean_abs_onset_ms": round(mean_abs, 2),
        "median_abs_onset_ms": round(mid, 2),
        "std_abs_onset_ms": round(std, 2),
        "cv_onset": round(cv, 4) if cv is not None else None,
        "p90_abs_onset_ms": round(p90, 2),
        "score": round(score, 4),
        "matched_timing_pairs": len(deltas_ms),
    }


def _weak_measures_ranked(weak_map: Dict[str, int]) -> List[Dict[str, Any]]:
    """按错音次数降序，便于前端与智能体直接消费。"""
    items: List[Dict[str, Any]] = []
    for k, v in (weak_map or {}).items():
        try:
            items.append({"measure": str(k), "error_count": int(v)})
        except (TypeError, ValueError):
            continue
    items.sort(key=lambda x: -x["error_count"])
    return items


def _build_session_stability(
    rhythm: Dict[str, Any],
    pitch: Dict[str, Any],
    note_counts: Dict[str, Any],
) -> Dict[str, Any]:
    """
    单次弹奏稳定性（不含力度）：起音一致性 + 错音密度 + 综合分 0–1（越高越稳）。
    """
    ref_n = note_counts.get("reference")
    try:
        ref_n_int = int(ref_n) if ref_n is not None else 0
    except (TypeError, ValueError):
        ref_n_int = 0
    err_total = int(pitch.get("error_total", 0))
    density = round(err_total / ref_n_int, 4) if ref_n_int > 0 else None

    timing_score = rhythm.get("score")
    timing_ok = bool(rhythm.get("available")) and timing_score is not None
    acc = float(pitch.get("accuracy", 0.0))

    composite: Optional[float] = None
    if timing_ok:
        ts = float(timing_score)
        if density is not None:
            dens_comp = max(0.0, min(1.0, 1.0 - min(1.0, density * 2.0)))
            composite = round(0.55 * ts + 0.25 * dens_comp + 0.20 * acc, 4)
        else:
            composite = round(0.65 * ts + 0.35 * acc, 4)
    else:
        composite = round(acc, 4)

    return {
        "timing_available": timing_ok,
        "timing_stability_score": timing_score,
        "onset_std_ms": rhythm.get("std_abs_onset_ms"),
        "onset_cv": rhythm.get("cv_onset"),
        "onset_p90_ms": rhythm.get("p90_abs_onset_ms"),
        "mean_onset_deviation_ms": rhythm.get("mean_abs_onset_ms"),
        "pitch_error_density": density,
        "composite_stability_score": composite,
        "note": "基于起音时间偏差与错音密度；不含力度。CV/σ 越大表示起音越不均匀。",
    }


def build_minimal_practice_metrics(
    accuracy: float,
    errors: List[ErrorLike],
) -> Dict[str, Any]:
    """无音符列表时仍可存盘：仅音准统计、薄弱小节（节奏指标不可用）。"""
    err_counts = _count_error_types(errors)
    total = len(errors)
    ratios = _pitch_error_ratios(err_counts, total)
    weak = _errors_by_measure(errors)
    pitch_obj = {
        "accuracy": round(float(accuracy), 6),
        **err_counts,
        "error_total": total,
        **ratios,
    }
    rhythm_empty = {
        "available": False,
        "reason": "no_note_snapshots",
        "mean_abs_onset_ms": None,
        "median_abs_onset_ms": None,
        "std_abs_onset_ms": None,
        "cv_onset": None,
        "p90_abs_onset_ms": None,
        "score": None,
        "matched_timing_pairs": 0,
    }
    nc = {"reference": None, "played": None}
    return {
        "schema_version": 3,
        "note_counts": nc,
        "pitch": pitch_obj,
        "rhythm": rhythm_empty,
        "weak_measures": weak,
        "weak_measures_ranked": _weak_measures_ranked(weak),
        "stability": _build_session_stability(rhythm_empty, pitch_obj, nc),
    }


def build_practice_metrics(
    reference: List[MidiNote],
    played: List[MidiNote],
    accuracy: float,
    errors: List[ErrorLike],
    *,
    pitch_tolerance_semitones: int = 1,
) -> Dict[str, Any]:
    """
    生成单次练习的结构化指标（schema_version 便于日后演进）。
    """
    rhythm = compute_rhythm_summary(reference, played, pitch_tolerance_semitones)
    err_counts = _count_error_types(errors)
    total = len(errors)
    ratios = _pitch_error_ratios(err_counts, total)
    weak = _errors_by_measure(errors)
    nc = {"reference": len(reference), "played": len(played)}
    pitch_obj = {
        "accuracy": round(float(accuracy), 6),
        **err_counts,
        "error_total": total,
        **ratios,
    }
    return {
        "schema_version": 3,
        "note_counts": nc,
        "pitch": pitch_obj,
        "rhythm": rhythm,
        "weak_measures": weak,
        "weak_measures_ranked": _weak_measures_ranked(weak),
        "stability": _build_session_stability(rhythm, pitch_obj, nc),
    }
