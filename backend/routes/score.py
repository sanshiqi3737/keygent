"""
标准乐谱 API：上传 PDF + MusicXML，获取乐谱图，支持按 score_id 比对。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import shutil
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from ..admin_auth import verify_admin_token
from ..auth_guard import require_login_user_id
from ..audio_processing.musicxml_parser import (
    parse_musicxml_techniques,
    is_musicxml_available,
)
from ..audio_processing.performance_metrics import (
    build_minimal_practice_metrics,
    build_practice_metrics,
)
from ..library_assessment import (
    assess_and_save_score_meta,
    load_score_meta,
    save_score_meta,
)
from ..paths import scores_data_dir
from ..practice_store import store_practice_audio_blob
from ..score_compare_service import (
    compare_musicxml_file_to_audio_file,
    midi_note_to_dict,
    serialize_errors_for_api,
)

router = APIRouter(prefix="/api/score", tags=["score"])
logger = logging.getLogger(__name__)


def _score_dir(score_id: str) -> Path:
    d = scores_data_dir() / score_id
    if not d.is_dir():
        raise HTTPException(status_code=404, detail="Score not found")
    return d


def _attach_uploader(root: Path, uploader_id: str) -> Dict[str, Any]:
    meta = load_score_meta(root) or {}
    if not isinstance(meta, dict):
        meta = {}
    meta["uploader_id"] = uploader_id
    save_score_meta(root, meta)
    return meta


def _can_manage_score(root: Path, user_id: str, x_admin_token: Optional[str]) -> bool:
    if verify_admin_token(x_admin_token):
        return True
    meta = load_score_meta(root) or {}
    uploader_id = str((meta or {}).get("uploader_id") or "").strip()
    # 兼容历史曲目（没有 uploader_id）先允许登录用户删除，后续可迁移后收紧
    if not uploader_id:
        return True
    return uploader_id == user_id


def _get_musicxml_path(root: Path) -> Path:
    """返回该乐谱目录下的 MusicXML 文件路径。"""
    for name in ("score.musicxml", "score.mxl", "score.xml"):
        cand = root / name
        if cand.exists():
            return cand
    for p in root.glob("*.musicxml"):
        return p
    for p in root.glob("*.mxl"):
        return p
    for p in root.glob("*.xml"):
        if p.name.lower().startswith("book"):
            continue
        return p
    raise HTTPException(status_code=404, detail="该乐谱包未找到 MusicXML")


def _pdf_page_to_image(pdf_path: Path, page_num: int, out_path: Path) -> None:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        mat = fitz.Matrix(2.0, 2.0)  # 2x for clarity
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(str(out_path))
        doc.close()
    except Exception as e:
        raise RuntimeError(f"PDF 转图失败: {e}") from e


@router.post("/upload")
async def score_upload(
    pdf: UploadFile = File(..., description="乐谱 PDF（必传）"),
    musicxml: UploadFile = File(..., description="MusicXML 标准答案 .musicxml/.mxl/.xml（必传）"),
    title: Optional[str] = Form(None, description="可选：用户自定义曲目名称"),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """
    上传标准乐谱：PDF（展示用）+ MusicXML（比对用）。返回 score_id 与页数。
    """
    uploader_id = require_login_user_id(authorization)
    if not is_musicxml_available():
        raise HTTPException(status_code=503, detail="需要安装 music21: pip install music21")

    score_id = str(uuid.uuid4())
    scores_data_dir().mkdir(parents=True, exist_ok=True)
    root = scores_data_dir() / score_id
    root.mkdir(parents=True, exist_ok=True)

    # 保存 PDF
    pdf_path = root / "score.pdf"
    pdf_path.write_bytes(await pdf.read())

    # 保存 MusicXML
    mx_name = musicxml.filename or "score.xml"
    if not mx_name.lower().endswith((".musicxml", ".xml", ".mxl")):
        mx_name += ".xml"
    musicxml_path = root / mx_name
    musicxml_path.write_bytes(await musicxml.read())

    # PDF 第一页转图
    try:
        _pdf_page_to_image(pdf_path, 1, root / "page_1.png")
        page_count = 1
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
        except Exception:
            pass
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    assessment_meta = None
    assessment_error = None
    title_hint = (title or "").strip() or (Path(mx_name).stem if mx_name else None)
    try:
        assessment_meta = await assess_and_save_score_meta(
            root,
            musicxml_path,
            title_hint=title_hint,
            enable_llm=True,
        )
    except Exception as e:
        # 评估失败不影响上传主流程
        assessment_error = str(e)
        if title_hint:
            # 至少落一份最小 meta，保证用户命名可见
            save_score_meta(
                root,
                {
                    "title": title_hint,
                    "difficulty": "unknown",
                    "abilities": [],
                    "assessment": {"method": "manual_title_only", "reason": "评估失败，保留用户命名"},
                },
            )
            assessment_meta = load_score_meta(root)

    # 记录上传者归属（公开谱库可见，后续可用于审计与权限控制）
    assessment_meta = _attach_uploader(root, uploader_id)

    return {
        "score_id": score_id,
        "page_count": page_count,
        "meta": assessment_meta,
        "meta_error": assessment_error,
    }


@router.delete("/{score_id}")
async def score_delete(
    score_id: str,
    authorization: Optional[str] = Header(default=None),
    x_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """删除指定曲目目录（含 PDF/MusicXML/图片/meta）。"""
    user_id = require_login_user_id(authorization)
    root = _score_dir(score_id)
    if not _can_manage_score(root, user_id, x_admin_token):
        raise HTTPException(status_code=403, detail="无权限删除该曲目（仅上传者或管理员可删）")
    try:
        shutil.rmtree(root)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e}") from e
    return {"deleted": True, "score_id": score_id}


@router.post("/delete-batch")
async def score_delete_batch(
    score_ids: List[str] = Body(..., embed=True, description="待删除 score_id 列表"),
    authorization: Optional[str] = Header(default=None),
    x_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """批量删除曲目。"""
    user_id = require_login_user_id(authorization)
    ok: List[str] = []
    failed: List[Dict[str, str]] = []
    unique_ids = []
    seen = set()
    for raw in score_ids:
        sid = str(raw or "").strip()
        if sid and sid not in seen:
            seen.add(sid)
            unique_ids.append(sid)
    for sid in unique_ids:
        root = scores_data_dir() / sid
        if not root.is_dir():
            failed.append({"score_id": sid, "reason": "not_found"})
            continue
        if not _can_manage_score(root, user_id, x_admin_token):
            failed.append({"score_id": sid, "reason": "forbidden"})
            continue
        try:
            shutil.rmtree(root)
            ok.append(sid)
        except Exception as e:
            failed.append({"score_id": sid, "reason": str(e)})
    return {
        "requested": len(unique_ids),
        "deleted_count": len(ok),
        "failed_count": len(failed),
        "deleted": ok,
        "failed": failed,
    }


@router.get("/{score_id}/image")
async def score_image(score_id: str, page: int = 1):
    """返回乐谱第 page 页的 PNG 图。"""
    root = _score_dir(score_id)
    img = root / f"page_{page}.png"
    if not img.exists():
        pdf_path = root / "score.pdf"
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="Score or page not found")
        _pdf_page_to_image(pdf_path, page, img)
    return FileResponse(img, media_type="image/png")


@router.get("/{score_id}/techniques")
async def score_techniques(score_id: str) -> Dict[str, Any]:
    """返回该乐谱中解析出的所有技巧：统计 counts 与事件列表 events（含小节、拍、音符名）。"""
    root = _score_dir(score_id)
    if not is_musicxml_available():
        raise HTTPException(status_code=503, detail="需要 music21")
    musicxml_path = _get_musicxml_path(root)
    counts, events = parse_musicxml_techniques(str(musicxml_path))
    return {"counts": counts, "events": events}


@router.get("/{score_id}/info")
async def score_info(score_id: str) -> Dict[str, Any]:
    """乐谱元信息：页数。"""
    root = _score_dir(score_id)
    page_count = 1
    pdf_path = root / "score.pdf"
    if pdf_path.exists():
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
        except Exception:
            pass
    return {"score_id": score_id, "page_count": page_count}


@router.get("/{score_id}/meta")
async def score_meta(score_id: str) -> Dict[str, Any]:
    """获取曲目元信息（title/difficulty/abilities/assessment）。"""
    root = _score_dir(score_id)
    meta = load_score_meta(root)
    if not meta:
        return {"score_id": score_id, "meta": None}
    return {"score_id": score_id, "meta": meta}


@router.post("/{score_id}/assess")
async def score_assess(
    score_id: str,
    use_llm: bool = Query(True, description="是否使用 LLM 对规则评估做细化"),
) -> Dict[str, Any]:
    """
    手动触发曲目评估并写入 meta.json（用于谱库难度/能力标签）。
    """
    root = _score_dir(score_id)
    musicxml_path = _get_musicxml_path(root)
    meta = await assess_and_save_score_meta(
        root,
        musicxml_path,
        title_hint=musicxml_path.stem,
        enable_llm=use_llm,
    )
    return {"score_id": score_id, "meta": meta}


@router.post("/assess-all")
async def score_assess_all(
    use_llm: bool = Query(True, description="是否使用 LLM 对规则评估做细化"),
    limit: int = Query(200, ge=1, le=1000, description="本次最多处理曲目数"),
) -> Dict[str, Any]:
    """
    批量重评估 data/scores 下已有曲目并写入各自 meta.json。
    """
    scores_data_dir().mkdir(parents=True, exist_ok=True)
    score_dirs = [p for p in scores_data_dir().iterdir() if p.is_dir()]
    score_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    processed: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for root in score_dirs[:limit]:
        score_id = root.name
        try:
            musicxml_path = _get_musicxml_path(root)
        except HTTPException as e:
            skipped.append({"score_id": score_id, "reason": str(e.detail)})
            continue
        try:
            meta = await assess_and_save_score_meta(
                root,
                musicxml_path,
                title_hint=musicxml_path.stem,
                enable_llm=use_llm,
            )
            processed.append(
                {
                    "score_id": score_id,
                    "difficulty": meta.get("difficulty"),
                    "abilities": meta.get("abilities"),
                }
            )
        except Exception as e:
            skipped.append({"score_id": score_id, "reason": str(e)})
    return {
        "total_candidates": min(len(score_dirs), limit),
        "processed_count": len(processed),
        "skipped_count": len(skipped),
        "processed": processed,
        "skipped": skipped,
    }


@router.get("/list")
async def score_list(
    q: Optional[str] = Query(None, description="按 score_id 或标题模糊搜索"),
    difficulty: Optional[str] = Query(None, description="按难度筛选，如 beginner/intermediate/advanced"),
    ability: Optional[str] = Query(None, description="按能力标签筛选（单个）"),
    limit: int = Query(200, ge=1, le=1000, description="最多返回数量"),
    include_meta: bool = Query(True, description="是否返回 meta 信息"),
) -> Dict[str, Any]:
    """
    获取曲库列表（按修改时间倒序）。
    """
    scores_data_dir().mkdir(parents=True, exist_ok=True)
    q_norm = (q or "").strip().lower()
    difficulty_norm = (difficulty or "").strip().lower()
    ability_norm = (ability or "").strip().lower()
    rows: List[Dict[str, Any]] = []
    score_dirs = [p for p in scores_data_dir().iterdir() if p.is_dir()]
    score_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for root in score_dirs:
        score_id = root.name
        need_meta = include_meta or bool(difficulty_norm) or bool(ability_norm)
        meta = load_score_meta(root) if need_meta else None
        title = str((meta or {}).get("title") or "")
        if q_norm:
            haystack = f"{score_id} {title}".lower()
            if q_norm not in haystack:
                continue
        if difficulty_norm:
            d = str((meta or {}).get("difficulty") or "").strip().lower()
            if d != difficulty_norm:
                continue
        if ability_norm:
            abilities = (meta or {}).get("abilities") or []
            ability_set = {str(x).strip().lower() for x in abilities if str(x).strip()}
            if ability_norm not in ability_set:
                continue
        row: Dict[str, Any] = {
            "score_id": score_id,
            "updated_at": int(root.stat().st_mtime),
        }
        if include_meta:
            row["meta"] = meta
            row["uploader_id"] = (meta or {}).get("uploader_id")
        rows.append(row)
        if len(rows) >= limit:
            break

    return {
        "count": len(rows),
        "rows": rows,
    }


def _user_performance_suffix(filename: Optional[str]) -> str:
    """临时文件扩展名：支持音频与 .mid/.midi。"""
    suf = Path(filename or "").suffix.lower()
    if suf in (".wav", ".mp3", ".flac", ".ogg", ".mid", ".midi"):
        return suf
    return ".wav"


@router.post("/{score_id}/compare")
async def score_compare(
    score_id: str,
    audio: UploadFile = File(..., description="用户弹奏：音频 wav/mp3/… 或 MIDI .mid/.midi"),
    use_multipitch: bool = Query(
        False,
        description="多声部检测（和弦/双手，CPU 很重；云端建议关，仅对音频有效）",
    ),
    compare_mode: Literal["beginner_pitch_only", "advanced_rhythm"] = Query(
        "beginner_pitch_only",
        description="初级仅看音准(beginner_pitch_only)；高级考虑节奏(advanced_rhythm)",
    ),
    start_measure: Optional[int] = Query(
        None,
        ge=1,
        description="练习起始小节（1-based）。仅 MusicXML reference 会裁剪。",
    ),
    end_measure: Optional[int] = Query(
        None,
        ge=1,
        description="练习结束小节（1-based，含）。仅 MusicXML reference 会裁剪。",
    ),
    include_note_snapshots: bool = Query(
        False,
        description="为 true 时额外返回 reference_notes/played_notes，供随后 POST /api/practice/sessions 存档（体积较大）",
    ),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """
    用已上传的标准乐谱与用户弹奏比对：支持 **音频**（转录）或 **MIDI**（直接解析）。
    返回准确率与错音列表（含 measure）。练习记录见 POST /api/practice/sessions。
    """
    user_id = require_login_user_id(authorization)
    root = _score_dir(score_id)
    musicxml_path = _get_musicxml_path(root)

    ext = _user_performance_suffix(audio.filename)
    tmp_user = root / f"_user_performance{ext}"
    try:
        try:
            audio_bytes = await audio.read()
            tmp_user.write_bytes(audio_bytes)

            def _run_compare_blocking():
                return compare_musicxml_file_to_audio_file(
                    str(musicxml_path),
                    tmp_user,
                    use_multipitch=use_multipitch,
                    compare_mode=compare_mode,
                    start_measure=start_measure,
                    end_measure=end_measure,
                )

            # 转录 + DTW 占满 CPU；放到线程池避免阻塞同进程其它请求（健康检查、登录等）
            ref_notes, user_notes, result = await asyncio.to_thread(_run_compare_blocking)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("score_compare failed for score_id=%s", score_id)
            msg = str(e).strip() or repr(e)
            raise HTTPException(
                status_code=500,
                detail=f"比对处理失败：{msg}（请优先尝试 WAV；MP3 需本机 ffmpeg；或换用 MIDI 排除转录问题）",
            ) from e

        errors = serialize_errors_for_api(result.errors)
        if compare_mode == "beginner_pitch_only":
            metrics = build_minimal_practice_metrics(result.accuracy, errors)
        else:
            metrics = build_practice_metrics(
                ref_notes, user_notes, result.accuracy, errors
            )
        resp: Dict[str, Any] = {
            "accuracy": result.accuracy,
            "errors": errors,
            "metrics": metrics,
            "compare_mode": compare_mode,
        }
        try:
            audio_meta = store_practice_audio_blob(user_id, audio_bytes, suffix=ext)
            resp["practice_audio_id"] = audio_meta.get("practice_audio_id")
            resp["practice_audio_relpath"] = audio_meta.get("practice_audio_relpath")
        except Exception:
            # 音频持久化失败不影响比对主流程
            logger.exception("failed to persist practice audio for user=%s", user_id)
        if include_note_snapshots:
            resp["reference_notes"] = [midi_note_to_dict(n) for n in ref_notes]
            resp["played_notes"] = [midi_note_to_dict(n) for n in user_notes]
        return resp
    finally:
        try:
            tmp_user.unlink(missing_ok=True)
        except Exception:
            pass
