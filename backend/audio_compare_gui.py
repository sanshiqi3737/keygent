"""
钢琴陪练 - 单页比对 GUI。核心逻辑与原版一致，仅调整界面展示。
"""
from __future__ import annotations

import threading
import traceback
from pathlib import Path
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

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
        key = round(err["time"], time_precision)
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
    return "八度" if has_octave else "和弦"


class CompareGUI(tk.Tk):
    """单页比对：标准 + 弹奏 → 准确率与错音（核心逻辑不变，仅单页展示）。"""

    def __init__(self) -> None:
        super().__init__()
        self.title("钢琴陪练 - 比对")
        self.geometry("720x520")
        self.minsize(400, 300)

        # 标准 (MIDI/MusicXML/音频)
        frm_ref = tk.Frame(self)
        frm_ref.pack(fill="x", padx=10, pady=(10, 5))
        tk.Label(frm_ref, text="标准 (MIDI/MusicXML/音频):").pack(side="left")
        self.entry_ref = tk.Entry(frm_ref)
        self.entry_ref.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(frm_ref, text="浏览文件...", command=self._browse_ref).pack(side="left")

        # 练习小节范围（仅 MusicXML 有效）
        frm_meas = tk.Frame(self)
        frm_meas.pack(fill="x", padx=10, pady=2)
        tk.Label(frm_meas, text="练习小节范围 (可选，仅 MusicXML):").pack(side="left")
        tk.Label(frm_meas, text="从").pack(side="left", padx=(0, 2))
        self.entry_start_measure = tk.Entry(frm_meas, width=5)
        self.entry_start_measure.pack(side="left", padx=2)
        tk.Label(frm_meas, text="到").pack(side="left", padx=2)
        self.entry_end_measure = tk.Entry(frm_meas, width=5)
        self.entry_end_measure.pack(side="left", padx=2)
        tk.Label(frm_meas, text="小节 (留空=全部)", fg="gray").pack(side="left", padx=2)

        # 你的弹奏 (MIDI/音频)
        frm_user = tk.Frame(self)
        frm_user.pack(fill="x", padx=10, pady=5)
        tk.Label(frm_user, text="你的弹奏 (MIDI/音频):").pack(side="left")
        self.entry_user = tk.Entry(frm_user)
        self.entry_user.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(frm_user, text="浏览...", command=self._browse_user).pack(side="left")

        # 检测模式：单音 / 多声部（多声部延迟检测，避免启动时加载 torch）
        frm_mode = tk.LabelFrame(self, text="检测模式")
        frm_mode.pack(fill="x", padx=10, pady=8)
        self.mode_var = tk.StringVar(value="single")
        tk.Radiobutton(
            frm_mode,
            text="单音检测（准确，适合单手、慢速）",
            variable=self.mode_var,
            value="single",
        ).pack(anchor="w")
        self.radio_multipitch = tk.Radiobutton(
            frm_mode,
            text="多声部（高级，和弦/双手，需预训练模型）",
            variable=self.mode_var,
            value="multipitch",
            state="disabled",
        )
        self.radio_multipitch.pack(anchor="w")
        self.lbl_multipitch_hint = tk.Label(
            frm_mode,
            text="正在检测多声部支持…",
            fg="gray",
        )
        self.lbl_multipitch_hint.pack(anchor="w")
        self.after(100, self._check_multipitch_async)

        # 比对按钮
        frm_btn = tk.Frame(self)
        frm_btn.pack(fill="x", padx=10, pady=10)
        self.btn_compare = tk.Button(
            frm_btn, text="开始比对", command=self._on_compare
        )
        self.btn_compare.pack(side="left")

        # 结果
        tk.Label(self, text="结果:").pack(anchor="w", padx=10)
        self.txt_result = scrolledtext.ScrolledText(self, wrap="word")
        self.txt_result.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _check_multipitch_async(self) -> None:
        """后台检测多声部支持，不阻塞主线程。"""
        def _do_check() -> None:
            try:
                ok = is_multipitch_available()
            except Exception:
                ok = False
            def _update() -> None:
                self.radio_multipitch.config(state="normal" if ok else "disabled")
                self.lbl_multipitch_hint.config(
                    text="" if ok else "未检测到多声部支持，请安装: pip install piano_transcription_inference torch"
                )
            self.after(0, _update)
        threading.Thread(target=_do_check, daemon=True).start()

    def _browse_ref(self) -> None:
        path = filedialog.askopenfilename(
            title="选择标准文件 (MIDI/MusicXML/音频)",
            filetypes=[
                ("All supported", "*.mid *.midi *.musicxml *.xml *.mxl *.wav *.mp3 *.flac *.ogg"),
                ("MusicXML", "*.musicxml *.xml *.mxl"),
                ("MIDI", "*.mid *.midi"),
                ("Audio", "*.wav *.mp3 *.flac *.ogg"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.entry_ref.delete(0, tk.END)
            self.entry_ref.insert(0, path)

    def _browse_user(self) -> None:
        path = filedialog.askopenfilename(
            title="选择你的弹奏文件 (MIDI/音频)",
            filetypes=[
                ("All supported", "*.mid *.midi *.wav *.mp3 *.flac *.ogg"),
                ("MIDI files", "*.mid *.midi"),
                ("Audio files", "*.wav *.mp3 *.flac *.ogg"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.entry_user.delete(0, tk.END)
            self.entry_user.insert(0, path)

    def _parse_measure(self, s: str) -> Optional[int]:
        s = (s or "").strip()
        if not s:
            return None
        try:
            n = int(s)
            return n if n >= 1 else None
        except ValueError:
            return None

    def _on_compare(self) -> None:
        ref_path_str = self.entry_ref.get().strip()
        user_path_str = self.entry_user.get().strip()
        if not ref_path_str or not user_path_str:
            messagebox.showwarning("提示", "请先选择标准文件和你的弹奏文件。")
            return
        ref_path = Path(ref_path_str)
        user_path = Path(user_path_str)
        if not ref_path.exists():
            messagebox.showerror("错误", f"标准文件不存在:\n{ref_path}")
            return
        if not user_path.exists():
            messagebox.showerror("错误", f"你的弹奏文件不存在:\n{user_path}")
            return
        self.btn_compare.config(state="disabled", text="正在比对...")
        self.txt_result.delete(1.0, tk.END)
        self.txt_result.insert(tk.END, "正在处理，请稍候…\n")
        thread = threading.Thread(
            target=self._run_compare,
            args=(ref_path, user_path),
            daemon=True,
        )
        thread.start()

    def _run_compare(self, ref_path: Path, user_path: Path) -> None:
        use_multipitch = self.mode_var.get() == "multipitch"
        try:
            if use_multipitch:
                self._append("检测模式: 多声部（高级）\n")
            self._append(f"加载标准: {ref_path}\n")
            start_m = self._parse_measure(self.entry_start_measure.get())
            end_m = self._parse_measure(self.entry_end_measure.get())
            if _is_musicxml_suffix(ref_path.suffix.lower()):
                if not is_musicxml_available():
                    self._append("错误: MusicXML 需要安装 music21 (pip install music21)\n")
                    messagebox.showerror("错误", "MusicXML 解析需要: pip install music21")
                    return
                if start_m is not None or end_m is not None:
                    self._append(f"  练习小节: {start_m or '首'} - {end_m or '末'}\n")
            try:
                ref_notes = load_notes_from_path(
                    ref_path,
                    use_multipitch=use_multipitch,
                    start_measure=start_m if _is_musicxml_suffix(ref_path.suffix.lower()) else None,
                    end_measure=end_m if _is_musicxml_suffix(ref_path.suffix.lower()) else None,
                )
            except RuntimeError as e:
                self._append(f"错误: {e}\n")
                messagebox.showerror("错误", str(e))
                return
            self._append(f"标准音符数: {len(ref_notes)}\n")
            self._append(f"加载你的弹奏: {user_path}\n")
            try:
                user_notes = load_notes_from_path(user_path, use_multipitch=use_multipitch)
            except RuntimeError as e:
                self._append(f"错误: {e}\n")
                messagebox.showerror("错误", str(e))
                return
            self._append(f"你的音符数: {len(user_notes)}\n")
            if not ref_notes:
                self._append("标准文件没有检测到音符，无法比较。\n")
                return
            result = compare_midi_note_sequences(ref_notes, user_notes, algorithm="enhanced")
            lines = []
            lines.append("\n=== 比对结果 ===\n")
            lines.append(f"准确率: {result.accuracy:.3f}\n")
            lines.append(f"错误总数: {len(result.errors)}\n")
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
                    {e.get("expected_name") for e in group if e.get("expected_name") is not None}
                )
                played_names = sorted(
                    {e.get("played_name") for e in group if e.get("played_name") is not None}
                )
                expected_str = ",".join(expected_names) if expected_names else "-"
                played_str = ",".join(played_names) if played_names else "-"
                label_str = f"{label} " if label else ""
                lines.append(
                    f"[{t:7.3f}s] {measure_str}{label_str}期望={expected_str} 实际={played_str}\n"
                )
            self._append("".join(lines))
        except Exception as exc:
            err_text = "".join(["发生错误：", str(exc), "\n", traceback.format_exc(), "\n"])
            self._append(err_text)
            messagebox.showerror("错误", f"比对过程中发生异常：\n{exc}")
        finally:
            self.after(0, lambda: self.btn_compare.config(state="normal", text="开始比对"))

    def _append(self, text: str) -> None:
        def _inner() -> None:
            self.txt_result.insert(tk.END, text)
            self.txt_result.see(tk.END)
        self.after(0, _inner)


def main() -> None:
    app = CompareGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
