from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pretty_midi


@dataclass
class MidiNote:
    """Simple representation of a MIDI note event."""

    pitch: int
    start: float
    end: float
    measure: Optional[int] = None  # 小节号（1-based），仅 MusicXML 等有小节信息时存在
    beat: Optional[float] = None  # 小节内拍位置（1.0=第一拍），用于分层比对与高亮


def parse_midi_to_notes(path: str) -> List[MidiNote]:
    """
    Parse a MIDI file into a flat list of notes.

    - Ignores drum channel (channel 9).
    - Returns notes sorted by start time.
    """
    midi = pretty_midi.PrettyMIDI(path)
    notes: List[MidiNote] = []

    for instrument in midi.instruments:
        # Skip drums to avoid noisy hits
        if instrument.is_drum:
            continue

        for note in instrument.notes:
            notes.append(
                MidiNote(
                    pitch=note.pitch,
                    start=float(note.start),
                    end=float(note.end),
                )
            )

    # Sort by onset time to get a clean sequence
    notes.sort(key=lambda n: n.start)
    return notes

