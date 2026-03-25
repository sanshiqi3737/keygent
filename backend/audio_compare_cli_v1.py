from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from audio_processing.midi_parser import MidiNote, parse_midi_to_notes
from audio_processing.note_transcriber import transcribe_audio_to_notes
from audio_processing.comparator import compare_midi_note_sequences


def load_notes_from_path(path: Path) -> List[MidiNote]:
    suffix = path.suffix.lower()
    if suffix in {".mid", ".midi"}:
        return parse_midi_to_notes(str(path))
    # Treat everything else as audio (wav/mp3/flac...)
    return transcribe_audio_to_notes(str(path))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare a reference performance with a user performance.\n"
            "Both files can be MIDI (.mid/.midi) or audio (wav/mp3/etc.).\n"
            "They will be converted to note sequences, then compared by pitch."
        )
    )

    parser.add_argument(
        "--reference",
        "-r",
        required=True,
        help="Path to reference file (MIDI or audio).",
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

    args = parser.parse_args()

    ref_path = Path(args.reference).expanduser().resolve()
    user_path = Path(args.user).expanduser().resolve()

    if not ref_path.exists():
        raise SystemExit(f"Reference file not found: {ref_path}")
    if not user_path.exists():
        raise SystemExit(f"User file not found: {user_path}")

    print(f"Loading reference from: {ref_path}")
    ref_notes = load_notes_from_path(ref_path)
    print(f"Reference notes: {len(ref_notes)}")

    print(f"Loading user performance from: {user_path}")
    user_notes = load_notes_from_path(user_path)
    print(f"User notes: {len(user_notes)}")

    result = compare_midi_note_sequences(
        reference=ref_notes,
        played=user_notes,
        pitch_tolerance_semitones=args.tolerance,
    )

    print("\n=== Compare Result ===")
    print(f"Accuracy: {result.accuracy:.3f}")
    print(f"Total errors: {len(result.errors)}")
    for err in result.errors:
        etype = err["type"]
        time = err["time"]
        expected_name = err.get("expected_name")
        played_name = err.get("played_name")
        if etype == "wrong":
            print(
                f"[{time:7.3f}s] WRONG   expected={expected_name} played={played_name}"
            )
        elif etype == "missed":
            print(
                f"[{time:7.3f}s] MISSED  expected={expected_name}"
            )
        elif etype == "extra":
            print(
                f"[{time:7.3f}s] EXTRA   played={played_name}"
            )


if __name__ == "__main__":
    main()

