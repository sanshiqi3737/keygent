"""
Parse MusicXML files to note sequences with measure and timing.

Provides: notes (as MidiNote), tempo (BPM), optional measure-range filter,
          and technique extraction (articulations, dynamics, etc.).
Requires: music21 (pip install music21).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .midi_parser import MidiNote

try:
    from music21 import converter, stream, tempo, chord, note
    from music21 import articulations
    from music21 import dynamics
    _MUSIC21_AVAILABLE = True
except ImportError:
    _MUSIC21_AVAILABLE = False
    articulations = None  # type: ignore
    dynamics = None  # type: ignore

# 技巧类型中文名（触键、力度等）
TECHNIQUE_NAMES: Dict[str, str] = {
    "Staccato": "断奏",
    "Staccatissimo": "短断奏",
    "Accent": "重音",
    "Tenuto": "保持",
    "Marcato": "顿音",
    "StrongAccent": "强重音",
    "Fermata": "延音",
    "Piano": "弱",
    "Pianissimo": "很弱",
    "Pianoissimo": "极弱",
    "MezzoPiano": "中弱",
    "MezzoForte": "中强",
    "Forte": "强",
    "Fortissimo": "很强",
    "FortePiano": "强后弱",
    "Crescendo": "渐强",
    "Diminuendo": "渐弱",
    "Decrescendo": "渐弱",
}

# music21: .flat 已弃用，用 .flatten()；和弦用 Chord + .pitches，多声部用 getOffsetInHierarchy 取时间


@dataclass
class MusicXMLInfo:
    """Metadata from MusicXML (for future use: key, time sig, etc.)."""
    bpm: float
    total_measures: int
    tempo_map: List[Tuple[float, float]]  # [(offset_quarter, bpm), ...] 用于变速转秒


def _quarter_to_seconds(offset_quarters: float, tempo_map: List[Tuple[float, float]]) -> float:
    """根据 tempo_map 将四分音符偏移转换为秒。"""
    if not tempo_map:
        return offset_quarters * 60.0 / 120.0
    tempo_map = sorted(tempo_map, key=lambda x: x[0])
    t_sec = 0.0
    prev_q = 0.0
    prev_bpm = tempo_map[0][1]
    for q, bpm in tempo_map:
        if q >= offset_quarters:
            t_sec += (offset_quarters - prev_q) * 60.0 / prev_bpm
            return t_sec
        t_sec += (q - prev_q) * 60.0 / prev_bpm
        prev_q, prev_bpm = q, bpm
    t_sec += (offset_quarters - prev_q) * 60.0 / prev_bpm
    return t_sec


def is_musicxml_available() -> bool:
    return _MUSIC21_AVAILABLE


def parse_musicxml_to_notes(
    path: str,
    start_measure: Optional[int] = None,
    end_measure: Optional[int] = None,
) -> Tuple[List[MidiNote], Optional[MusicXMLInfo]]:
    """
    Parse a MusicXML file into a list of MidiNote (pitch, start, end in seconds).

    - path: path to .musicxml / .xml / .mxl
    - start_measure, end_measure: 1-based measure range (inclusive). If given,
      only notes in [start_measure, end_measure] are returned. Use for "practice
      measures 12-30" feature.
    - Returns (notes, info). info has bpm and total_measures; notes are sorted by start.
    """
    if not _MUSIC21_AVAILABLE:
        raise RuntimeError("MusicXML 解析需要安装: pip install music21")

    score = converter.parse(path)
    flat = score.flatten()
    notes_flat = list(flat.notesAndRests)

    # 收集所有速度标记 (offset_quarter, bpm)，用于变速转秒
    tempo_map: List[Tuple[float, float]] = [(0.0, 120.0)]
    try:
        for el in flat:
            if isinstance(el, tempo.MetronomeMark) and el.number is not None:
                try:
                    q = float(el.getOffsetInHierarchy(score))
                except Exception:
                    q = float(el.offset)
                tempo_map.append((q, float(el.number)))
    except Exception:
        pass
    tempo_map = sorted(tempo_map, key=lambda x: x[0])
    # 去重：同一 offset 只保留最后一个
    seen = set()
    unique = []
    for q, bpm in reversed(tempo_map):
        if q not in seen:
            seen.add(q)
            unique.append((q, bpm))
    tempo_map = list(reversed(unique))
    if not tempo_map or tempo_map[0][0] > 0:
        tempo_map.insert(0, (0.0, 120.0))
    bpm = tempo_map[0][1]

    result: List[MidiNote] = []
    max_measure = 0

    for n in notes_flat:
        measure_num = None
        measure_offset_q = None
        try:
            meas = n.getContextByClass(stream.Measure)
            if meas is not None and hasattr(meas, "number"):
                measure_num = meas.number
                if measure_num is not None:
                    max_measure = max(max_measure, measure_num)
                try:
                    measure_offset_q = float(meas.getOffsetInHierarchy(score))
                except Exception:
                    try:
                        measure_offset_q = float(meas.getOffsetInHierarchy(flat))
                    except Exception:
                        measure_offset_q = float(getattr(meas, "offset", 0) or 0)
        except Exception:
            pass

        if start_measure is not None and measure_num is not None and measure_num < start_measure:
            continue
        if end_measure is not None and measure_num is not None and measure_num > end_measure:
            continue

        try:
            offset_quarters = float(n.getOffsetInHierarchy(score))
        except Exception:
            try:
                offset_quarters = float(n.getOffsetInHierarchy(flat))
            except Exception:
                offset_quarters = float(getattr(n, "offset", 0))
        duration_quarters = n.duration.quarterLength
        start_sec = _quarter_to_seconds(offset_quarters, tempo_map)
        end_sec = _quarter_to_seconds(offset_quarters + duration_quarters, tempo_map)

        # 小节内拍：1.0 = 第一拍（按四分音符计）
        beat_val: Optional[float] = None
        if measure_offset_q is not None:
            beat_val = 1.0 + (offset_quarters - measure_offset_q)

        kw: dict = {}
        if measure_num is not None:
            kw["measure"] = measure_num
        if beat_val is not None:
            kw["beat"] = beat_val
        if isinstance(n, chord.Chord):
            for p in sorted(n.pitches, key=lambda x: x.midi):
                try:
                    midi_num = p.midi
                    result.append(
                        MidiNote(pitch=int(midi_num), start=start_sec, end=end_sec, **kw)
                    )
                except Exception:
                    continue
        elif isinstance(n, note.Note):
            try:
                midi_num = n.pitch.midi
                result.append(
                    MidiNote(pitch=int(midi_num), start=start_sec, end=end_sec, **kw)
                )
            except Exception:
                continue
        else:
            if hasattr(n, "pitches") and getattr(n, "pitches", None):
                for p in sorted(n.pitches, key=lambda x: getattr(x, "midi", 0)):
                    try:
                        midi_num = p.midi
                        result.append(
                            MidiNote(pitch=int(midi_num), start=start_sec, end=end_sec, **kw)
                        )
                    except Exception:
                        continue
            elif hasattr(n, "pitch") and getattr(n, "pitch", None) is not None:
                try:
                    midi_num = n.pitch.midi
                    result.append(
                        MidiNote(pitch=int(midi_num), start=start_sec, end=end_sec, **kw)
                    )
                except Exception:
                    pass

    result.sort(key=lambda n: (n.start, n.pitch))
    info = MusicXMLInfo(
        bpm=bpm,
        total_measures=max_measure if max_measure else 1,
        tempo_map=tempo_map,
    )
    return result, info


@dataclass
class TechniqueEvent:
    """单条技巧事件，用于列表展示。"""
    technique_type: str   # 英文类型，如 Staccato, Forte
    name_cn: str          # 中文名
    measure: Optional[int] = None
    beat: Optional[float] = None
    note_name: Optional[str] = None  # 如 C4


def _note_display_name(n) -> Optional[str]:
    """从 music21 Note/Chord 取显示名。"""
    try:
        if isinstance(n, chord.Chord):
            return ",".join(p.nameWithOctave for p in sorted(n.pitches, key=lambda x: x.midi))
        if hasattr(n, "pitch"):
            return n.pitch.nameWithOctave
    except Exception:
        pass
    return None


def parse_musicxml_techniques(path: str) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """
    从 MusicXML 解析所有技巧（触键、力度等），返回统计与事件列表。

    - path: .musicxml / .xml / .mxl 路径
    - 返回 (counts, events): counts 为 { "技巧英文": 次数 }，events 为每条事件的详情列表，
      每项含 type, name_cn, measure, beat, note_name，用于前端展示。
    """
    if not _MUSIC21_AVAILABLE:
        raise RuntimeError("MusicXML 解析需要安装: pip install music21")

    score = converter.parse(path)
    flat = score.flatten()
    notes_flat = list(flat.notesAndRests)
    counts: Dict[str, int] = {}
    events: List[Dict[str, Any]] = []

    # 力度标记：每个标记算一处，带小节信息
    try:
        if dynamics:
            dyn_elements = flat.getElementsByClass(dynamics.Dynamic)
            for d in dyn_elements:
                tname = type(d).__name__
                if tname not in TECHNIQUE_NAMES:
                    TECHNIQUE_NAMES.setdefault(tname, tname)
                counts[tname] = counts.get(tname, 0) + 1
                measure_num = None
                try:
                    meas = d.getContextByClass(stream.Measure)
                    if meas is not None and hasattr(meas, "number"):
                        measure_num = meas.number
                except Exception:
                    pass
                events.append({
                    "type": tname,
                    "name_cn": TECHNIQUE_NAMES.get(tname, tname),
                    "measure": measure_num,
                    "beat": None,
                    "note_name": None,
                })
            # 渐强/渐弱（Wedge 或 Crescendo/Diminuendo 类）
            wedge_class = getattr(dynamics, "DynamicWedge", None)
            cresc_class = getattr(dynamics, "Crescendo", None)
            dim_class = getattr(dynamics, "Diminuendo", None)
            for el in flat:
                name = None
                if wedge_class and isinstance(el, wedge_class):
                    name = "Crescendo" if getattr(el, "type", None) == "crescendo" else "Diminuendo"
                elif cresc_class and isinstance(el, cresc_class):
                    name = "Crescendo"
                elif dim_class and isinstance(el, dim_class):
                    name = "Diminuendo"
                if name:
                    if name not in TECHNIQUE_NAMES:
                        TECHNIQUE_NAMES[name] = name
                    counts[name] = counts.get(name, 0) + 1
                    try:
                        meas = el.getContextByClass(stream.Measure)
                        measure_num = meas.number if meas and hasattr(meas, "number") else None
                    except Exception:
                        measure_num = None
                    events.append({
                        "type": name,
                        "name_cn": TECHNIQUE_NAMES.get(name, name),
                        "measure": measure_num,
                        "beat": None,
                        "note_name": None,
                    })
    except Exception:
        pass

    for n in notes_flat:
        if not hasattr(n, "pitches") and not hasattr(n, "pitch"):
            continue
        measure_num = None
        measure_offset_q = None
        try:
            meas = n.getContextByClass(stream.Measure)
            if meas is not None and hasattr(meas, "number"):
                measure_num = meas.number
                try:
                    measure_offset_q = float(meas.getOffsetInHierarchy(score))
                except Exception:
                    try:
                        measure_offset_q = float(meas.getOffsetInHierarchy(flat))
                    except Exception:
                        measure_offset_q = float(getattr(meas, "offset", 0) or 0)
        except Exception:
            pass
        try:
            offset_quarters = float(n.getOffsetInHierarchy(score))
        except Exception:
            try:
                offset_quarters = float(n.getOffsetInHierarchy(flat))
            except Exception:
                offset_quarters = float(getattr(n, "offset", 0))
        beat_val = None
        if measure_offset_q is not None:
            beat_val = round(1.0 + (offset_quarters - measure_offset_q), 2)
        note_name = _note_display_name(n)

        # 触键与表情（每个音上的 articulations / expressions）
        art_list = []
        if hasattr(n, "articulations") and n.articulations:
            art_list.extend(n.articulations)
        if hasattr(n, "expressions") and n.expressions:
            art_list.extend(n.expressions)
        for art in art_list:
            tname = type(art).__name__
            if tname not in TECHNIQUE_NAMES:
                TECHNIQUE_NAMES.setdefault(tname, tname)
            counts[tname] = counts.get(tname, 0) + 1
            events.append({
                "type": tname,
                "name_cn": TECHNIQUE_NAMES.get(tname, tname),
                "measure": measure_num,
                "beat": beat_val,
                "note_name": note_name,
            })

    return counts, events
