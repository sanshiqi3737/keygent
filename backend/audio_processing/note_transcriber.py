from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List, Optional

import librosa
import numpy as np

from ..paths import project_root
from .midi_parser import MidiNote, parse_midi_to_notes

# Optional: ByteDance-style multi-pitch model (piano_transcription_inference)
# 延迟导入，避免启动时加载 torch
_MULTIPITCH_AVAILABLE: Optional[bool] = None
_MULTIPITCH_MODULES: Optional[dict] = None  # {PianoTranscription, SAMPLE_RATE, torch}


_PROJECT_ROOT = project_root()
_DEFAULT_CHECKPOINT = _PROJECT_ROOT / "CRNN_note_F1=0.9677_pedal_F1=0.9186.pth"


def _env_hop_length(default: int = 256) -> int:
    """PIANO_TRANSCRIBE_HOP_LENGTH 越大越快、略粗；建议 256–512（云端可试 384/512）。"""
    try:
        h = int(os.environ.get("PIANO_TRANSCRIBE_HOP_LENGTH", str(default)))
    except ValueError:
        return default
    return max(128, min(1024, h))


def _load_multipitch() -> bool:
    """延迟加载多声部模块，仅首次调用时执行。"""
    global _MULTIPITCH_AVAILABLE, _MULTIPITCH_MODULES
    if _MULTIPITCH_AVAILABLE is not None:
        return _MULTIPITCH_AVAILABLE
    try:
        from piano_transcription_inference import (
            PianoTranscription,
            sample_rate as MULTIPITCH_SAMPLE_RATE,
        )
        import torch
        _MULTIPITCH_MODULES = {
            "PianoTranscription": PianoTranscription,
            "SAMPLE_RATE": MULTIPITCH_SAMPLE_RATE,
            "torch": torch,
        }
        _MULTIPITCH_AVAILABLE = True
    except ImportError:
        _MULTIPITCH_MODULES = None
        _MULTIPITCH_AVAILABLE = False
    return _MULTIPITCH_AVAILABLE


def transcribe_audio_to_notes(
    path: str,
    sr: int = 22050,
    fmin: float = 65.0,
    fmax: float = 2093.0,
    frame_length: int = 2048,
    hop_length: Optional[int] = None,
    min_note_duration: float = 0.08,
) -> List[MidiNote]:
    """
    Transcribe an audio file (WAV/MP3/...) into a sequence of MidiNote.

    - Uses librosa.pyin for pitch tracking.
    - Uses onset detection to segment notes.
    - Ignores very short segments (min_note_duration, in seconds).
    """
    hl = hop_length if hop_length is not None else _env_hop_length()
    y, sr = librosa.load(path, sr=sr, mono=True)

    if y.size == 0:
        return []

    # Fundamental frequency estimation (Hz)
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=fmin,
        fmax=fmax,
        sr=sr,
        frame_length=frame_length,
        hop_length=hl,
    )

    # Time positions for each frame
    frame_times = librosa.frames_to_time(
        np.arange(len(f0)), sr=sr, hop_length=hl
    )

    # Onset detection to determine note boundaries
    onset_frames = librosa.onset.onset_detect(
        y=y, sr=sr, hop_length=hl, backtrack=True
    )

    # Ensure we have at least a start and end; otherwise treat whole clip as one region
    if len(onset_frames) == 0:
        onset_frames = np.array([0, len(f0) - 1], dtype=int)
    elif len(onset_frames) == 1:
        onset_frames = np.concatenate(
            [onset_frames, np.array([len(f0) - 1], dtype=int)]
        )

    notes: List[MidiNote] = []

    for i in range(len(onset_frames) - 1):
        start_frame = int(onset_frames[i])
        end_frame = int(onset_frames[i + 1])
        if end_frame <= start_frame:
            continue

        segment_slice = slice(start_frame, end_frame)
        seg_f0 = f0[segment_slice]

        # Keep only voiced frames
        valid = ~np.isnan(seg_f0)
        if not np.any(valid):
            continue

        seg_f0_valid = seg_f0[valid]

        # Convert to MIDI pitch (float), then take median
        seg_midi = librosa.hz_to_midi(seg_f0_valid)
        median_midi = float(np.median(seg_midi))
        midi_pitch = int(round(median_midi))

        start_time = float(frame_times[start_frame])
        end_time = float(frame_times[end_frame])

        if (end_time - start_time) < min_note_duration:
            continue

        notes.append(MidiNote(pitch=midi_pitch, start=start_time, end=end_time))

    return notes


def is_multipitch_available() -> bool:
    """Return True if the ByteDance-style multi-pitch transcription model is available."""
    return _load_multipitch()


def get_default_multipitch_checkpoint() -> Optional[Path]:
    """返回项目根目录下的预训练 .pth 路径（若存在）。"""
    if _DEFAULT_CHECKPOINT.is_file():
        return _DEFAULT_CHECKPOINT
    return None


def transcribe_audio_to_notes_multipitch(
    path: str,
    device: str = "cpu",
    checkpoint_path: Optional[str] = None,
) -> List[MidiNote]:
    """
    Transcribe audio to notes using a multi-pitch (piano) model (e.g. ByteDance).

    checkpoint_path: 可选。不传则优先使用项目根目录下的
     CRNN_note_F1=0.9677_pedal_F1=0.9186.pth（即 D:\\piano_project_2\\ 下）。
    """
    if not _load_multipitch() or _MULTIPITCH_MODULES is None:
        raise RuntimeError(
            "多声部转录需要安装: pip install piano_transcription_inference torch"
        )
    torch = _MULTIPITCH_MODULES["torch"]
    PianoTranscription = _MULTIPITCH_MODULES["PianoTranscription"]
    MULTIPITCH_SAMPLE_RATE = _MULTIPITCH_MODULES["SAMPLE_RATE"]

    path = str(Path(path).resolve())
    # 用 librosa 加载，避免 piano_transcription_inference 的 load_audio 与新版 librosa.resample 不兼容
    audio, _ = librosa.load(path, sr=MULTIPITCH_SAMPLE_RATE, mono=True)
    if audio.size == 0:
        return []

    cp = checkpoint_path
    if not cp:
        default = get_default_multipitch_checkpoint()
        cp = str(default) if default else None
    dev = torch.device(device)
    transcriptor = PianoTranscription(checkpoint_path=cp, device=dev)

    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
        out_midi = f.name
    try:
        transcriptor.transcribe(audio, out_midi)
        notes = parse_midi_to_notes(out_midi)
    finally:
        Path(out_midi).unlink(missing_ok=True)

    return notes

