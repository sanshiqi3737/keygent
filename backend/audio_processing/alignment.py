"""
DTW-based time alignment for note sequences.

Aligns reference and played notes by onset time so that timing drift
does not cause paired misalignment or pitch swaps.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from .midi_parser import MidiNote

try:
    from dtw import dtw
    _DTW_AVAILABLE = True
except ImportError:
    _DTW_AVAILABLE = False


def dtw_align_notes(
    reference: List[MidiNote],
    played: List[MidiNote],
    chord_time_window_s: float = 0.15,
) -> Tuple[List[Tuple[int, int]], List[int], List[int], List[MidiNote], List[MidiNote]]:
    """
    Align reference and played note sequences by onset time using DTW.

    Returns:
        matched_pairs: list of (ref_index, play_index) for one-to-one aligned pairs
        missed_ref: list of reference indices with no matching played note
        extra_play: list of played indices with no matching reference note
        ref_sorted: reference notes sorted by (quantized_time, pitch)
        play_sorted: played notes sorted by (quantized_time, pitch)
    """
    if not _DTW_AVAILABLE:
        raise RuntimeError("DTW 对齐需要安装: pip install dtw-python")

    if chord_time_window_s and chord_time_window_s > 0:
        def _sort_key(n: MidiNote) -> tuple:
            t = round(n.start / chord_time_window_s) * chord_time_window_s
            return (t, n.pitch)
        ref_sorted = sorted(reference, key=_sort_key)
        play_sorted = sorted(played, key=_sort_key)
    else:
        ref_sorted = sorted(reference, key=lambda n: (n.start, n.pitch))
        play_sorted = sorted(played, key=lambda n: (n.start, n.pitch))

    n_ref = len(ref_sorted)
    n_play = len(play_sorted)
    if n_ref == 0:
        return [], [], list(range(n_play)), ref_sorted, play_sorted
    if n_play == 0:
        return [], list(range(n_ref)), [], ref_sorted, play_sorted

    ref_times = np.array([note.start for note in ref_sorted], dtype=np.float64)
    play_times = np.array([note.start for note in play_sorted], dtype=np.float64)

    # DTW: x=query (ref), y=reference (play). index1 -> ref, index2 -> play
    # Reshape to (N,1) for cdist
    alignment = dtw(
        ref_times.reshape(-1, 1),
        play_times.reshape(-1, 1),
        keep_internals=True,
        step_pattern="symmetric2",
    )
    index1 = np.array(alignment.index1)
    index2 = np.array(alignment.index2)

    # Collect all (i, j) pairs on the path
    path_pairs = list(zip(index1.tolist(), index2.tolist()))

    # One-to-one assignment: sort by time difference, greedily assign
    path_pairs_with_cost = [
        (i, j, abs(ref_sorted[i].start - play_sorted[j].start))
        for (i, j) in path_pairs
    ]
    path_pairs_with_cost.sort(key=lambda x: x[2])

    assigned_ref = set()
    assigned_play = set()
    matched_pairs: List[Tuple[int, int]] = []
    for i, j, _ in path_pairs_with_cost:
        if i not in assigned_ref and j not in assigned_play:
            matched_pairs.append((i, j))
            assigned_ref.add(i)
            assigned_play.add(j)

    matched_pairs.sort(key=lambda p: (ref_sorted[p[0]].start, ref_sorted[p[0]].pitch))
    missed_ref = sorted(set(range(n_ref)) - assigned_ref)
    extra_play = sorted(set(range(n_play)) - assigned_play)

    return matched_pairs, missed_ref, extra_play, ref_sorted, play_sorted


# 联合时间+音高 DTW 的默认参数
_T_MAX = 2.0  # 最大允许时间偏移（秒）
_P_MAX = 12.0  # 音高差上限（半音）
_W_TIME = 0.5
_W_PITCH = 0.5


def combined_dtw_align(
    reference: List[MidiNote],
    played: List[MidiNote],
    chord_time_window_s: float = 0.15,
    t_max: float = _T_MAX,
    p_max: float = _P_MAX,
    w_time: float = _W_TIME,
    w_pitch: float = _W_PITCH,
) -> Tuple[List[Tuple[int, int]], List[int], List[int], List[MidiNote], List[MidiNote]]:
    """
    联合时间和音高的 DTW 对齐：代价 = w_time * |Δt|/T_max + w_pitch * min(|Δp|, P_max)/P_max。
    返回与 dtw_align_notes 相同的 5 元组。
    """
    if not _DTW_AVAILABLE:
        raise RuntimeError("DTW 对齐需要安装: pip install dtw-python")

    ref_sorted = sorted(reference, key=lambda n: (n.start, n.pitch))
    play_sorted = sorted(played, key=lambda n: (n.start, n.pitch))
    n_ref = len(ref_sorted)
    n_play = len(play_sorted)
    if n_ref == 0:
        return [], [], list(range(n_play)), ref_sorted, play_sorted
    if n_play == 0:
        return [], list(range(n_ref)), [], ref_sorted, play_sorted

    ref_t = np.array([n.start for n in ref_sorted], dtype=np.float64)
    ref_p = np.array([n.pitch for n in ref_sorted], dtype=np.float64)
    play_t = np.array([n.start for n in play_sorted], dtype=np.float64)
    play_p = np.array([n.pitch for n in play_sorted], dtype=np.float64)
    t_max = max(t_max, 1e-6)
    p_max = max(p_max, 1e-6)
    scale_t = np.sqrt(w_time) / t_max
    scale_p = np.sqrt(w_pitch) / p_max
    x_ref = np.column_stack([ref_t * scale_t, ref_p * scale_p])
    y_play = np.column_stack([play_t * scale_t, play_p * scale_p])

    alignment = dtw(
        x_ref,
        y_play,
        keep_internals=True,
        step_pattern="symmetric2",
    )
    index1 = np.array(alignment.index1)
    index2 = np.array(alignment.index2)
    path_pairs = list(zip(index1.tolist(), index2.tolist()))

    def cost(i: int, j: int) -> float:
        dt = min(abs(ref_t[i] - play_t[j]), t_max) / t_max
        dp = min(abs(ref_p[i] - play_p[j]), p_max) / p_max
        return w_time * dt + w_pitch * dp

    path_with_cost = [(i, j, cost(i, j)) for (i, j) in path_pairs]
    path_with_cost.sort(key=lambda x: x[2])
    assigned_ref = set()
    assigned_play = set()
    matched_pairs: List[Tuple[int, int]] = []
    for i, j, _ in path_with_cost:
        if i not in assigned_ref and j not in assigned_play:
            matched_pairs.append((i, j))
            assigned_ref.add(i)
            assigned_play.add(j)

    matched_pairs.sort(key=lambda p: (ref_sorted[p[0]].start, ref_sorted[p[0]].pitch))
    missed_ref = sorted(set(range(n_ref)) - assigned_ref)
    extra_play = sorted(set(range(n_play)) - assigned_play)
    return matched_pairs, missed_ref, extra_play, ref_sorted, play_sorted


def is_dtw_available() -> bool:
    return _DTW_AVAILABLE
