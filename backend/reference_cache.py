"""
MusicXML 解析结果内存缓存（按路径 + mtime + 小节范围失效）。

减轻同一乐谱多次比对时的 music21 解析开销；多 worker 时每进程独立一份缓存。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# key -> (mtime_ns, notes, info)
_cache: Dict[str, Tuple[int, List[Any], Any]] = {}
_MAX_ENTRIES = 128


def _make_key(path: Path, start_measure: Optional[int], end_measure: Optional[int]) -> str:
    return f"{path.resolve()}|{start_measure}|{end_measure}"


def clear_musicxml_cache() -> None:
    """测试或热更新乐谱时可清空缓存。"""
    _cache.clear()


def get_cached_musicxml_notes(
    path: str,
    start_measure: Optional[int] = None,
    end_measure: Optional[int] = None,
) -> Tuple[List[Any], Any]:
    """
    返回与 parse_musicxml_to_notes 相同结构 (notes, info)。
    文件变更（mtime）后自动重解析。
    """
    try:
        from .audio_processing.musicxml_parser import parse_musicxml_to_notes
    except ImportError:
        from audio_processing.musicxml_parser import parse_musicxml_to_notes

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(path)
    mtime_ns = p.stat().st_mtime_ns
    key = _make_key(p, start_measure, end_measure)

    hit = _cache.get(key)
    if hit is not None and hit[0] == mtime_ns:
        return hit[1], hit[2]

    notes, info = parse_musicxml_to_notes(str(p.resolve()), start_measure, end_measure)

    if len(_cache) >= _MAX_ENTRIES:
        for i, k in enumerate(list(_cache.keys())):
            if i >= _MAX_ENTRIES // 2:
                break
            _cache.pop(k, None)

    _cache[key] = (mtime_ns, notes, info)
    return notes, info
