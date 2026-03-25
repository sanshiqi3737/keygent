"""
乐谱 + 用户音频比对（纯业务逻辑，供 score 路由与 practice 路由共用）。

不包含 HTTP 与持久化，避免核心比对与智能体/练习记录耦合。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple

from fastapi import HTTPException

from .audio_processing.comparator import CompareResult, compare_midi_note_sequences
from .audio_processing.musicxml_parser import is_musicxml_available
from .reference_cache import get_cached_musicxml_notes
from .audio_processing.note_transcriber import (
    transcribe_audio_to_notes,
    transcribe_audio_to_notes_multipitch,
    is_multipitch_available,
)
from .audio_processing.midi_parser import MidiNote, parse_midi_to_notes


def _cleanup_transcribed_notes(
    notes: List[MidiNote],
    *,
    min_note_duration_s: float = 0.10,
    same_pitch_merge_window_s: float = 0.09,
) -> List[MidiNote]:
    """
    对音频转录结果做轻量去噪：
    1) 去掉极短音符；
    2) 合并同音高且时间非常接近/重叠的碎片。
    """
    if not notes:
        return []

    filtered = [
        n for n in notes if (float(n.end) - float(n.start)) >= min_note_duration_s
    ]
    if not filtered:
        return []
    filtered.sort(key=lambda n: (float(n.start), int(n.pitch)))

    merged: List[MidiNote] = []
    for n in filtered:
        if not merged:
            merged.append(n)
            continue
        prev = merged[-1]
        if (
            prev.pitch == n.pitch
            and float(n.start) <= float(prev.end) + same_pitch_merge_window_s
        ):
            # 合并同音高碎片，避免一个长音被拆成多个 extra/missed
            merged[-1] = MidiNote(
                pitch=prev.pitch,
                start=float(prev.start),
                end=max(float(prev.end), float(n.end)),
                measure=prev.measure,
                beat=prev.beat,
            )
        else:
            merged.append(n)
    return merged


def midi_note_to_dict(n: MidiNote) -> Dict[str, Any]:
    d: Dict[str, Any] = {"pitch": n.pitch, "start": float(n.start), "end": float(n.end)}
    if getattr(n, "measure", None) is not None:
        d["measure"] = int(n.measure)  # type: ignore[arg-type]
    if getattr(n, "beat", None) is not None:
        d["beat"] = float(n.beat)  # type: ignore[arg-type]
    return d


def dict_to_midi_note(d: Dict[str, Any]) -> MidiNote:
    return MidiNote(
        pitch=int(d["pitch"]),
        start=float(d["start"]),
        end=float(d["end"]),
        measure=int(d["measure"]) if d.get("measure") is not None else None,
        beat=float(d["beat"]) if d.get("beat") is not None else None,
    )


def serialize_errors_for_api(errors: List[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for e in errors:
        err = dict(e)
        if err.get("measure") is not None:
            err["measure"] = int(err["measure"])
        out.append(err)
    return out


def compare_musicxml_file_to_audio_file(
    musicxml_path: str,
    user_performance_path: Path,
    *,
    use_multipitch: bool = False,
    compare_mode: Literal["beginner_pitch_only", "advanced_rhythm"] = "advanced_rhythm",
    start_measure: int | None = None,
    end_measure: int | None = None,
) -> Tuple[List[MidiNote], List[MidiNote], CompareResult]:
    """
    解析标准 MusicXML 与用户「弹奏」文件，返回 (ref_notes, user_notes, compare_result)。

    用户文件可以是：
    - **.mid / .midi**：按 MIDI 解析（不走转录；`use_multipitch` 忽略）
    - **音频**（wav/mp3 等）：走转录；可选 multipitch

    调用方负责写入 user_performance_path 并在之后删除临时文件。
    """
    if not is_musicxml_available():
        raise HTTPException(status_code=503, detail="需要 music21")

    ref_notes, _ = get_cached_musicxml_notes(
        musicxml_path, start_measure=start_measure, end_measure=end_measure
    )
    if not ref_notes:
        raise HTTPException(status_code=400, detail="标准乐谱未解析到音符，请检查 MusicXML 文件")

    suf = user_performance_path.suffix.lower()
    is_midi_input = suf in (".mid", ".midi")
    if is_midi_input:
        user_notes = parse_midi_to_notes(str(user_performance_path))
        if not user_notes:
            raise HTTPException(
                status_code=400,
                detail="用户 MIDI 未解析到音符（或非标准 MIDI），请检查文件",
            )
    elif use_multipitch and is_multipitch_available():
        try:
            user_notes = transcribe_audio_to_notes_multipitch(
                str(user_performance_path), device="cpu"
            )
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
    else:
        # 音频宽松档：抬高最短音符时长，减少噪声造成的“多音/漏音”。
        user_notes = transcribe_audio_to_notes(
            str(user_performance_path),
            min_note_duration=0.10,
        )
        user_notes = _cleanup_transcribed_notes(
            user_notes,
            min_note_duration_s=0.10,
            same_pitch_merge_window_s=0.09,
        )

    if not user_notes:
        raise HTTPException(
            status_code=400,
            detail="未能从用户文件得到音符（若为音频请检查格式/内容；MIDI 见上条）",
        )

    # 让 reference 的时间轴从 0 开始：因为用户音频/片段从自身起点开始
    # 切掉前段后，reference 也需要对齐到同一起点，避免“明明同一段却差一段时间”的误判。
    ref_min_start = min(float(n.start) for n in ref_notes) if ref_notes else 0.0
    user_min_start = min(float(n.start) for n in user_notes) if user_notes else 0.0

    if ref_min_start and abs(ref_min_start) > 1e-9:
        ref_notes = [
            MidiNote(
                pitch=n.pitch,
                start=float(n.start) - ref_min_start,
                end=float(n.end) - ref_min_start,
                measure=n.measure,
                beat=n.beat,
            )
            for n in ref_notes
        ]

    if user_min_start and abs(user_min_start) > 1e-9:
        user_notes = [
            MidiNote(
                pitch=n.pitch,
                start=float(n.start) - user_min_start,
                end=float(n.end) - user_min_start,
                measure=n.measure,
                beat=n.beat,
            )
            for n in user_notes
        ]

    if is_midi_input:
        # MIDI 输入保持较严格，避免掩盖真实音高错误。
        if compare_mode == "beginner_pitch_only":
            result = compare_midi_note_sequences(
                ref_notes,
                user_notes,
                algorithm="edit_distance",
                pitch_tolerance_semitones=2,
                chord_time_window_s=0.25,
            )
        else:
            result = compare_midi_note_sequences(
                ref_notes,
                user_notes,
                algorithm="enhanced",
            )
    else:
        if compare_mode == "beginner_pitch_only":
            # 初级：只看音准，弱化节奏影响（更大的时间窗口 + 编辑距离）。
            result = compare_midi_note_sequences(
                ref_notes,
                user_notes,
                algorithm="edit_distance",
                # 赦免区间再放宽一档，优先降低“本来没那么多错音”的体感偏差
                pitch_tolerance_semitones=6,
                chord_time_window_s=0.50,
            )
        else:
            # 高级：音准 + 节奏，保留 enhanced。
            result = compare_midi_note_sequences(
                ref_notes,
                user_notes,
                algorithm="enhanced",
                pitch_tolerance_semitones=3,
                chord_time_window_s=0.25,
                segment_duration_s=1.0,
                merge_time_thresh=0.28,
                merge_pitch_thresh=2,
            )
    return ref_notes, user_notes, result
