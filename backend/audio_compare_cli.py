from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional

from audio_processing.midi_parser import MidiNote, parse_midi_to_notes
from audio_processing.note_transcriber import (
    transcribe_audio_to_notes,
    transcribe_audio_to_notes_multipitch,
    is_multipitch_available,
)
from audio_processing.comparator import compare_midi_note_sequences, ErrorEvent
from audio_processing.musicxml_parser import is_musicxml_available
from reference_cache import get_cached_musicxml_notes


def _is_musicxml_suffix(suffix: str) -> bool:
    return suffix in {".musicxml", ".xml", ".mxl"}


def load_notes_from_path(
    path: Path,
    use_multipitch: bool = False,
    start_measure: Optional[int] = None,
    end_measure: Optional[int] = None,
) -> List[MidiNote]:
    suffix = path.suffix.lower()
    if suffix in {".mid", ".midi"}:
        return parse_midi_to_notes(str(path))
    if _is_musicxml_suffix(suffix):
        notes, _ = get_cached_musicxml_notes(
            str(path),
            start_measure=start_measure,
            end_measure=end_measure,
        )
        return notes
    if use_multipitch and is_multipitch_available():
        return transcribe_audio_to_notes_multipitch(str(path), device="cpu")
    return transcribe_audio_to_notes(str(path))


def _group_errors_by_time(
    errors: List[ErrorEvent], time_precision: int = 2
) -> Dict[float, List[ErrorEvent]]:
    groups: Dict[float, List[ErrorEvent]] = {}
    for err in errors:
        t = err["time"]
        key = round(t, time_precision)
        groups.setdefault(key, []).append(err)
    return groups


def _detect_chord_label(group: List[ErrorEvent]) -> str:
    expected_pitches: List[int] = []
    played_pitches: List[int] = []
    for e in group:
        if "expected" in e:
            expected_pitches.append(int(e["expected"]))
        if "played" in e:
            played_pitches.append(int(e["played"]))

    if len(set(expected_pitches)) <= 1 and len(set(played_pitches)) <= 1:
        return ""

    pitches = sorted(set(expected_pitches + played_pitches))

    has_octave = False
    for i in range(len(pitches)):
        for j in range(i + 1, len(pitches)):
            if abs(pitches[j] - pitches[i]) % 12 == 0:
                has_octave = True
                break
        if has_octave:
            break

    if has_octave:
        return "OCTAVE"
    return "CHORD"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare a reference performance with a user performance.\n"
            "Reference: MIDI / MusicXML (.musicxml .xml .mxl) / audio. User: MIDI or audio.\n"
            "MusicXML 作为标准时可用 --start-measure/--end-measure 指定练习小节范围."
        )
    )

    parser.add_argument(
        "--reference",
        "-r",
        required=True,
        help="标准文件：MIDI、MusicXML 或音频.",
    )
    parser.add_argument(
        "--user",
        "-u",
        required=True,
        help="Path to user performance file (MIDI or audio).",
    )
    parser.add_argument(
        "--tolerance",
        "-t",
        type=int,
        default=1,
        help="Pitch tolerance in semitones for a note to be considered correct (default: 1).",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["single", "multipitch"],
        default="single",
        help="single: 单音检测（准确）. multipitch: 多声部/和弦（需安装 piano_transcription_inference）.",
    )
    parser.add_argument(
        "--start-measure",
        type=int,
        default=None,
        metavar="N",
        help="仅练习从第 N 小节开始（标准为 MusicXML 时有效，1-based）。",
    )
    parser.add_argument(
        "--end-measure",
        type=int,
        default=None,
        metavar="N",
        help="仅练习到第 N 小节结束（标准为 MusicXML 时有效，1-based）。",
    )

    args = parser.parse_args()

    ref_path = Path(args.reference).expanduser().resolve()
    user_path = Path(args.user).expanduser().resolve()

    if not ref_path.exists():
        raise SystemExit(f"Reference file or folder not found: {ref_path}")
    if not user_path.exists():
        raise SystemExit(f"User file not found: {user_path}")

    use_multipitch = args.mode == "multipitch"
    if use_multipitch and not is_multipitch_available():
        raise SystemExit(
            "多声部模式需要: pip install piano_transcription_inference"
        )

    if _is_musicxml_suffix(ref_path.suffix.lower()) and not is_musicxml_available():
        raise SystemExit("标准为 MusicXML 时需要: pip install music21")

    print(f"Loading reference from: {ref_path} (mode={args.mode})")
    ref_notes = load_notes_from_path(
        ref_path,
        use_multipitch=use_multipitch,
        start_measure=args.start_measure,
        end_measure=args.end_measure,
    )
    if args.start_measure is not None or args.end_measure is not None:
        print(f"  Measure range: {args.start_measure or '?'} - {args.end_measure or '?'}")
    print(f"Reference notes: {len(ref_notes)}")

    print(f"Loading user performance from: {user_path}")
    user_notes = load_notes_from_path(user_path, use_multipitch=use_multipitch)
    print(f"User notes: {len(user_notes)}")

    result = compare_midi_note_sequences(
        reference=ref_notes,
        played=user_notes,
        pitch_tolerance_semitones=args.tolerance,
    )

    print("\n=== Compare Result ===")
    print(f"Accuracy: {result.accuracy:.3f}")
    print(f"Total errors: {len(result.errors)}")
    grouped = _group_errors_by_time(result.errors)
    for t in sorted(grouped.keys()):
        group = grouped[t]
        measure_str = ""
        for e in group:
            if e.get("measure") is not None:
                measure_str = f"第{e['measure']}小节 "
                break
        label = _detect_chord_label(group)
        expected_names = sorted(
            {
                e.get("expected_name")
                for e in group
                if e.get("expected_name") is not None
            }
        )
        played_names = sorted(
            {
                e.get("played_name")
                for e in group
                if e.get("played_name") is not None
            }
        )
        expected_str = ",".join(expected_names) if expected_names else "-"
        played_str = ",".join(played_names) if played_names else "-"
        label_str = f"{label} " if label else ""
        print(
            f"[{t:7.3f}s] {measure_str}{label_str}expected={expected_str} played={played_str}"
        )


if __name__ == "__main__":
    main()

