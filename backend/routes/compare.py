from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from ..audio_processing.midi_parser import parse_midi_to_notes
from ..audio_processing.comparator import compare_midi_note_sequences
from ..audio_processing.note_transcriber import (
    transcribe_audio_to_notes,
    transcribe_audio_to_notes_multipitch,
    is_multipitch_available,
)
from ..audio_processing.musicxml_parser import (
    parse_musicxml_to_notes,
    is_musicxml_available,
)

router = APIRouter(prefix="/compare", tags=["compare"])


def _ensure_midi(file: UploadFile) -> None:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mid", ".midi"}:
        raise HTTPException(status_code=400, detail="Only MIDI files are supported for now.")


@router.post("/midi-midi")
async def compare_midi_midi(
    reference_file: UploadFile = File(...),
    played_file: UploadFile = File(...),
    algorithm: str = Query("edit_distance", description="edit_distance | dtw | enhanced"),
) -> Dict[str, Any]:
    """
    Compare a reference MIDI with a played MIDI.

    Returns:
    - accuracy: float
    - errors: list of {type, time, expected?, played?, measure?, beat?}
    """
    _ensure_midi(reference_file)
    _ensure_midi(played_file)

    temp_dir = Path("tmp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    ref_path = temp_dir / "reference.mid"
    play_path = temp_dir / "played.mid"

    ref_bytes = await reference_file.read()
    play_bytes = await played_file.read()
    ref_path.write_bytes(ref_bytes)
    play_path.write_bytes(play_bytes)

    reference_notes = parse_midi_to_notes(str(ref_path))
    played_notes = parse_midi_to_notes(str(play_path))

    if not reference_notes:
        raise HTTPException(status_code=400, detail="标准 MIDI 未解析到音符，无法比对")

    algo = algorithm if algorithm in ("edit_distance", "dtw", "enhanced") else "edit_distance"
    result = compare_midi_note_sequences(
        reference_notes,
        played_notes,
        algorithm=algo,
    )

    return {
        "accuracy": result.accuracy,
        "errors": result.errors,
    }


def _is_musicxml_suffix(suffix: str) -> bool:
    return suffix in {".musicxml", ".xml", ".mxl"}


def _load_notes_from_upload(
    temp_dir: Path,
    upload: UploadFile,
    start_measure: Optional[int] = None,
    end_measure: Optional[int] = None,
    use_multipitch: bool = False,
) -> Any:
    """
    Save upload to temp file, then parse to MidiNote list.
    - MIDI -> parse_midi_to_notes
    - MusicXML -> parse_musicxml_to_notes (optional start_measure, end_measure)
    - else -> transcribe as audio (single or multipitch)
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "").suffix.lower()

    if suffix in {".mid", ".midi"}:
        tmp_path = temp_dir / f"{upload.filename or 'file'}.mid"
        data = upload.file.read()
        tmp_path.write_bytes(data)
        return parse_midi_to_notes(str(tmp_path))

    if _is_musicxml_suffix(suffix):
        name = upload.filename or "score"
        if not name.lower().endswith((".musicxml", ".xml", ".mxl")):
            name += ".xml"
        tmp_path = temp_dir / name
        data = upload.file.read()
        tmp_path.write_bytes(data)
        notes, _ = parse_musicxml_to_notes(
            str(tmp_path),
            start_measure=start_measure,
            end_measure=end_measure,
        )
        return notes

    # treat as audio
    tmp_path = temp_dir / (upload.filename or "audio")
    data = upload.file.read()
    tmp_path.write_bytes(data)
    if use_multipitch and is_multipitch_available():
        return transcribe_audio_to_notes_multipitch(str(tmp_path), device="cpu")
    return transcribe_audio_to_notes(str(tmp_path))


@router.post("")
async def compare_any(
    reference_file: UploadFile = File(..., description="标准文件：MIDI / MusicXML / 音频"),
    played_file: UploadFile = File(..., description="用户弹奏：MIDI 或音频"),
    start_measure: Optional[int] = Query(None, description="练习起始小节(1-based)，仅当标准为 MusicXML 时有效"),
    end_measure: Optional[int] = Query(None, description="练习结束小节(1-based)，仅当标准为 MusicXML 时有效"),
    algorithm: str = Query("enhanced", description="edit_distance | dtw | enhanced"),
    use_multipitch: bool = Query(False, description="多声部检测（和弦/双手，需 piano_transcription_inference）"),
) -> Dict[str, Any]:
    """
    通用比对接口：支持 MIDI / MusicXML / 音频 作为标准，用户弹奏为 MIDI 或音频。
    algorithm=enhanced 时使用联合 DTW + 匈牙利 + 后处理，推荐用于有节奏波动或和弦。
    """
    if use_multipitch and not is_multipitch_available():
        raise HTTPException(
            status_code=503,
            detail="多声部模式需要安装: pip install piano_transcription_inference torch",
        )

    temp_dir = Path("tmp") / "uploads"

    ref_suffix = Path(reference_file.filename or "").suffix.lower()
    reference_notes = _load_notes_from_upload(
        temp_dir,
        reference_file,
        start_measure=start_measure if _is_musicxml_suffix(ref_suffix) else None,
        end_measure=end_measure if _is_musicxml_suffix(ref_suffix) else None,
        use_multipitch=use_multipitch,
    )
    played_notes = _load_notes_from_upload(temp_dir, played_file, use_multipitch=use_multipitch)

    if not reference_notes:
        raise HTTPException(status_code=400, detail="标准文件未解析到音符，无法比对")

    algo = algorithm if algorithm in ("edit_distance", "dtw", "enhanced") else "enhanced"
    result = compare_midi_note_sequences(
        reference_notes,
        played_notes,
        algorithm=algo,
    )

    return {
        "accuracy": result.accuracy,
        "errors": result.errors,
    }


