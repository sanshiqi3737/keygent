from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple, TypedDict

import numpy as np
from scipy.optimize import linear_sum_assignment

from .midi_parser import MidiNote
from .alignment import dtw_align_notes, combined_dtw_align, is_dtw_available


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_to_name(midi: int) -> str:
    """
    Convert MIDI number to note name like C3, D#4, etc.

    Uses the common convention: 60 -> C4.
    """
    octave = (midi // 12) - 1
    name = NOTE_NAMES[midi % 12]
    return f"{name}{octave}"


class ErrorEvent(TypedDict, total=False):
    type: Literal["wrong", "missed", "extra"]
    time: float
    expected: int
    played: int
    expected_name: str
    played_name: str
    measure: int  # 小节号（1-based），有参考小节信息时显示
    beat: float  # 小节内拍位置，用于高亮


@dataclass
class CompareResult:
    accuracy: float
    errors: List[ErrorEvent]


def compare_midi_note_sequences(
    reference: List[MidiNote],
    played: List[MidiNote],
    pitch_tolerance_semitones: int = 1,
    chord_time_window_s: float = 0.15,
    use_dtw: bool = False,
    algorithm: Literal["edit_distance", "dtw", "enhanced"] = "edit_distance",
    segment_duration_s: float = 0.5,
    merge_time_thresh: float = 0.1,
    merge_pitch_thresh: int = 1,
) -> CompareResult:
    """
    Compare two note sequences. algorithm: edit_distance (default), dtw, enhanced.

    - enhanced: 联合时间+音高 DTW，按时间窗分段 + 匈牙利多对多匹配，后处理合并微小误差。
    - dtw: 仅时间 DTW 后贪心配对再比音高。
    - edit_distance: 编辑距离（Levenshtein）。
    - segment_duration_s: enhanced 算法的时间窗大小（秒），快曲可减小、慢曲可增大。
    """
    if algorithm == "enhanced" and is_dtw_available():
        return compare_with_enhanced_dtw(
            reference,
            played,
            pitch_tolerance_semitones=pitch_tolerance_semitones,
            chord_time_window_s=chord_time_window_s,
            segment_duration_s=segment_duration_s,
            merge_time_thresh=merge_time_thresh,
            merge_pitch_thresh=merge_pitch_thresh,
        )
    if (algorithm == "dtw" or use_dtw) and is_dtw_available():
        return _compare_with_dtw(
            reference, played, pitch_tolerance_semitones, chord_time_window_s
        )
    return _compare_edit_distance(
        reference, played, pitch_tolerance_semitones, chord_time_window_s
    )


def match_notes_hungarian(
    ref_notes: List[MidiNote],
    play_notes: List[MidiNote],
    tolerance: int,
    penalty: float = 1e9,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """
    一个时间窗内的多对多匹配：用匈牙利算法按音高差最小配对。
    返回 (matched_pairs, missed_ref_indices, extra_play_indices)。
    """
    n, m = len(ref_notes), len(play_notes)
    if n == 0:
        return [], [], list(range(m))
    if m == 0:
        return [], list(range(n)), []
    cost = np.zeros((n, m))
    for i in range(n):
        for j in range(m):
            d = abs(ref_notes[i].pitch - play_notes[j].pitch)
            cost[i, j] = d if d <= 12 else 13
    N = max(n, m)
    cost_pad = np.full((N, N), penalty)
    cost_pad[:n, :m] = cost
    for k in range(min(N - n, N - m)):
        cost_pad[n + k, m + k] = 0
    row_ind, col_ind = linear_sum_assignment(cost_pad)
    matched: List[Tuple[int, int]] = []
    for k in range(N):
        i, j = int(row_ind[k]), int(col_ind[k])
        if i < n and j < m and cost[i, j] <= tolerance:
            matched.append((i, j))
    missed = [i for i in range(n) if i not in [p[0] for p in matched]]
    extra = [j for j in range(m) if j not in [p[1] for p in matched]]
    return matched, missed, extra


def _merge_tiny_errors(errors: List[ErrorEvent], time_thresh: float = 0.1, pitch_thresh: int = 1) -> List[ErrorEvent]:
    """
    相邻的 (extra, missed) 若时间差 < time_thresh 且音高差 <= pitch_thresh，视为时间微偏，合并移除一对。
    """
    out: List[ErrorEvent] = []
    used = set()
    for i, e in enumerate(errors):
        if i in used:
            continue
        if e.get("type") == "missed":
            continue
        if e.get("type") != "extra":
            out.append(e)
            continue
        t_play = e.get("time") or 0
        p_play = e.get("played")
        if p_play is None:
            out.append(e)
            continue
        best_j = None
        for j, e2 in enumerate(errors):
            if j <= i or j in used or e2.get("type") != "missed":
                continue
            t_ref = e2.get("time") or 0
            p_ref = e2.get("expected")
            if p_ref is None:
                continue
            if abs(t_play - t_ref) < time_thresh and abs((p_play or 0) - (p_ref or 0)) <= pitch_thresh:
                best_j = j
                break
        if best_j is not None:
            used.add(i)
            used.add(best_j)
            continue
        out.append(e)
    for j, e in enumerate(errors):
        if j in used or e.get("type") != "missed":
            continue
        out.append(e)
    out.sort(key=lambda x: x.get("time") or 0)
    return out


def compare_with_enhanced_dtw(
    reference: List[MidiNote],
    played: List[MidiNote],
    pitch_tolerance_semitones: int = 1,
    chord_time_window_s: float = 0.15,
    segment_duration_s: float = 0.5,
    merge_time_thresh: float = 0.1,
    merge_pitch_thresh: int = 1,
) -> CompareResult:
    """
    增强比对：联合 DTW 对齐 → 按时间窗分段 → 段内匈牙利匹配 → 后处理合并微小误差。
    错误带 measure、beat 便于前端高亮。
    """
    if not reference:
        return CompareResult(accuracy=1.0, errors=[])
    ref_sorted = sorted(reference, key=lambda n: (n.start, n.pitch))
    play_sorted = sorted(played, key=lambda n: (n.start, n.pitch))
    if not play_sorted:
        errors = [
            _err_missed(ref_sorted[i], pitch_tolerance_semitones)
            for i in range(len(ref_sorted))
        ]
        return CompareResult(accuracy=0.0, errors=errors)

    matched_pairs, missed_ref, extra_play, ref_sorted, play_sorted = combined_dtw_align(
        reference, played, chord_time_window_s=chord_time_window_s
    )
    n_ref, n_play = len(ref_sorted), len(play_sorted)
    ref_t_min, ref_t_max = ref_sorted[0].start, ref_sorted[-1].start
    play_t_min, play_t_max = play_sorted[0].start, play_sorted[-1].start
    ref_span = max(ref_t_max - ref_t_min, 1e-9)
    play_span = max(play_t_max - play_t_min, 1e-9)
    play_to_ref_time = {}
    for i, j in matched_pairs:
        play_to_ref_time[j] = ref_sorted[i].start
    for j in range(n_play):
        if j not in play_to_ref_time:
            play_to_ref_time[j] = ref_t_min + (play_sorted[j].start - play_t_min) * ref_span / play_span

    seg_ref: dict = {}
    seg_play: dict = {}
    for i in range(n_ref):
        sid = int(ref_sorted[i].start / segment_duration_s)
        seg_ref.setdefault(sid, []).append(i)
    for j in range(n_play):
        sid = int(play_to_ref_time[j] / segment_duration_s)
        seg_play.setdefault(sid, []).append(j)

    all_seg_ids = sorted(set(seg_ref) | set(seg_play))
    errors: List[ErrorEvent] = []
    correct_count = 0
    for sid in all_seg_ids:
        ri = seg_ref.get(sid, [])
        pj = seg_play.get(sid, [])
        ref_seg = [ref_sorted[i] for i in ri]
        play_seg = [play_sorted[j] for j in pj]
        seg_matched, seg_missed, seg_extra = match_notes_hungarian(
            ref_seg, play_seg, pitch_tolerance_semitones
        )
        for (li, lj) in seg_matched:
            i, j = ri[li], pj[lj]
            if abs(ref_sorted[i].pitch - play_sorted[j].pitch) <= pitch_tolerance_semitones:
                correct_count += 1
            else:
                errors.append(
                    _err_wrong(ref_sorted[i], play_sorted[j], pitch_tolerance_semitones)
                )
        for li in seg_missed:
            errors.append(_err_missed(ref_sorted[ri[li]], pitch_tolerance_semitones))
        for lj in seg_extra:
            errors.append(_err_extra(play_sorted[pj[lj]], pitch_tolerance_semitones))

    errors = _merge_tiny_errors(
        errors,
        time_thresh=merge_time_thresh,
        pitch_thresh=merge_pitch_thresh,
    )
    ref_count = max(1, len(reference))
    accuracy = correct_count / ref_count
    return CompareResult(accuracy=accuracy, errors=errors)


def _err_wrong(ref_note: MidiNote, play_note: MidiNote, _tolerance: int) -> ErrorEvent:
    e: ErrorEvent = {
        "type": "wrong",
        "time": float(play_note.start),
        "expected": int(ref_note.pitch),
        "played": int(play_note.pitch),
        "expected_name": midi_to_name(ref_note.pitch),
        "played_name": midi_to_name(play_note.pitch),
    }
    if getattr(ref_note, "measure", None) is not None:
        e["measure"] = ref_note.measure
    if getattr(ref_note, "beat", None) is not None:
        e["beat"] = ref_note.beat
    return e


def _err_missed(ref_note: MidiNote, _tolerance: int) -> ErrorEvent:
    e: ErrorEvent = {
        "type": "missed",
        "time": float(ref_note.start),
        "expected": int(ref_note.pitch),
        "expected_name": midi_to_name(ref_note.pitch),
    }
    if getattr(ref_note, "measure", None) is not None:
        e["measure"] = ref_note.measure
    if getattr(ref_note, "beat", None) is not None:
        e["beat"] = ref_note.beat
    return e


def _err_extra(play_note: MidiNote, _tolerance: int) -> ErrorEvent:
    return {
        "type": "extra",
        "time": float(play_note.start),
        "played": int(play_note.pitch),
        "played_name": midi_to_name(play_note.pitch),
    }


def _compare_with_dtw(
    reference: List[MidiNote],
    played: List[MidiNote],
    pitch_tolerance_semitones: int,
    chord_time_window_s: float,
) -> CompareResult:
    """DTW 时间对齐后逐对比较音高。"""
    matched_pairs, missed_ref, extra_play, ref_sorted, play_sorted = dtw_align_notes(
        reference, played, chord_time_window_s=chord_time_window_s
    )
    errors: List[ErrorEvent] = []
    correct_count = 0
    for ref_i, play_j in matched_pairs:
        ref_note = ref_sorted[ref_i]
        played_note = play_sorted[play_j]
        if abs(ref_note.pitch - played_note.pitch) <= pitch_tolerance_semitones:
            correct_count += 1
        else:
            errors.append(
                ErrorEvent(
                    type="wrong",
                    time=float(played_note.start),
                    expected=int(ref_note.pitch),
                    played=int(played_note.pitch),
                    expected_name=midi_to_name(ref_note.pitch),
                    played_name=midi_to_name(played_note.pitch),
                    **({"measure": ref_note.measure} if getattr(ref_note, "measure", None) is not None else {}),
                )
            )
    for ref_i in missed_ref:
        ref_note = ref_sorted[ref_i]
        errors.append(
            ErrorEvent(
                type="missed",
                time=float(ref_note.start),
                expected=int(ref_note.pitch),
                expected_name=midi_to_name(ref_note.pitch),
                **({"measure": ref_note.measure} if getattr(ref_note, "measure", None) is not None else {}),
            )
        )
    for play_j in extra_play:
        played_note = play_sorted[play_j]
        errors.append(
            ErrorEvent(
                type="extra",
                time=float(played_note.start),
                played=int(played_note.pitch),
                played_name=midi_to_name(played_note.pitch),
            )
        )
    errors.sort(key=lambda e: e["time"])
    reference_count = max(1, len(reference))
    accuracy = correct_count / reference_count
    return CompareResult(accuracy=accuracy, errors=errors)


def _compare_edit_distance(
    reference: List[MidiNote],
    played: List[MidiNote],
    pitch_tolerance_semitones: int,
    chord_time_window_s: float,
) -> CompareResult:
    """原有编辑距离比对逻辑。"""
    if chord_time_window_s and chord_time_window_s > 0:
        def _sort_key(n: MidiNote) -> tuple:
            t = round(n.start / chord_time_window_s) * chord_time_window_s
            return (t, n.pitch)
        reference = sorted(reference, key=_sort_key)
        played = sorted(played, key=_sort_key)

    ref_pitches = [n.pitch for n in reference]
    play_pitches = [n.pitch for n in played]

    n = len(ref_pitches)
    m = len(play_pitches)

    # DP matrix for Levenshtein distance
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][0] = i  # deletions (missed notes)
    for j in range(1, m + 1):
        dp[0][j] = j  # insertions (extra notes)

    def pitch_cost(a: int, b: int) -> int:
        return 0 if abs(a - b) <= pitch_tolerance_semitones else 1

    # Fill DP table
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost_sub = dp[i - 1][j - 1] + pitch_cost(ref_pitches[i - 1], play_pitches[j - 1])
            cost_del = dp[i - 1][j] + 1  # missed reference note
            cost_ins = dp[i][j - 1] + 1  # extra played note
            dp[i][j] = min(cost_sub, cost_del, cost_ins)

    # Backtrack to get alignment and classify events
    i, j = n, m
    errors: List[ErrorEvent] = []
    correct_count = 0

    while i > 0 or j > 0:
        if i > 0 and j > 0:
            current = dp[i][j]
            diag = dp[i - 1][j - 1]
            up = dp[i - 1][j]
            left = dp[i][j - 1]

            # Prefer substitution/match when cost matches
            if current == diag + pitch_cost(ref_pitches[i - 1], play_pitches[j - 1]):
                ref_note = reference[i - 1]
                played_note = played[j - 1]
                if abs(ref_note.pitch - played_note.pitch) <= pitch_tolerance_semitones:
                    correct_count += 1
                else:
                    _m = getattr(ref_note, "measure", None)
                    errors.append(
                        ErrorEvent(
                            type="wrong",
                            time=float(played_note.start),
                            expected=int(ref_note.pitch),
                            played=int(played_note.pitch),
                            expected_name=midi_to_name(int(ref_note.pitch)),
                            played_name=midi_to_name(int(played_note.pitch)),
                            **({"measure": _m} if _m is not None else {}),
                        )
                    )
                i -= 1
                j -= 1
                continue

            # Deletion: missed reference note
            if current == up + 1:
                ref_note = reference[i - 1]
                _m = getattr(ref_note, "measure", None)
                errors.append(
                    ErrorEvent(
                        type="missed",
                        time=float(ref_note.start),
                        expected=int(ref_note.pitch),
                        expected_name=midi_to_name(int(ref_note.pitch)),
                        **({"measure": _m} if _m is not None else {}),
                    )
                )
                i -= 1
                continue

            # Insertion: extra played note
            if current == left + 1:
                played_note = played[j - 1]
                errors.append(
                    ErrorEvent(
                        type="extra",
                        time=float(played_note.start),
                        played=int(played_note.pitch),
                        played_name=midi_to_name(int(played_note.pitch)),
                    )
                )
                j -= 1
                continue

        elif i > 0:
            # Remaining reference notes are missed
            ref_note = reference[i - 1]
            _m = getattr(ref_note, "measure", None)
            errors.append(
                ErrorEvent(
                    type="missed",
                    time=float(ref_note.start),
                    expected=int(ref_note.pitch),
                    expected_name=midi_to_name(int(ref_note.pitch)),
                    **({"measure": _m} if _m is not None else {}),
                )
            )
            i -= 1
        else:
            # Remaining played notes are extras
            played_note = played[j - 1]
            errors.append(
                ErrorEvent(
                    type="extra",
                    time=float(played_note.start),
                    played=int(played_note.pitch),
                    played_name=midi_to_name(int(played_note.pitch)),
                )
            )
            j -= 1

    reference_count = max(1, len(reference))
    accuracy = correct_count / reference_count

    # Reverse errors to be in chronological/alignment order
    errors.reverse()

    return CompareResult(accuracy=accuracy, errors=errors)

