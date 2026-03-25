from __future__ import annotations

import threading
import traceback
from pathlib import Path
from typing import List

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from audio_processing.midi_parser import MidiNote, parse_midi_to_notes
from audio_processing.note_transcriber import transcribe_audio_to_notes
from audio_processing.comparator import compare_midi_note_sequences


def load_notes_from_path(path: Path) -> List[MidiNote]:
    suffix = path.suffix.lower()
    if suffix in {".mid", ".midi"}:
        return parse_midi_to_notes(str(path))
    # Treat everything else as audio (wav/mp3/flac...)
    return transcribe_audio_to_notes(str(path))


class PianoTutorGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Piano Tutor - Pitch Compare")
        self.geometry("720x520")

        # Reference file
        frm_ref = tk.Frame(self)
        frm_ref.pack(fill="x", padx=10, pady=(10, 5))

        tk.Label(frm_ref, text="标准文件 (MIDI/音频):").pack(side="left")
        self.entry_ref = tk.Entry(frm_ref)
        self.entry_ref.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(frm_ref, text="浏览...", command=self.browse_reference).pack(
            side="left"
        )

        # User file
        frm_user = tk.Frame(self)
        frm_user.pack(fill="x", padx=10, pady=5)

        tk.Label(frm_user, text="你的弹奏 (MIDI/音频):").pack(side="left")
        self.entry_user = tk.Entry(frm_user)
        self.entry_user.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(frm_user, text="浏览...", command=self.browse_user).pack(side="left")

        # Compare button
        frm_btn = tk.Frame(self)
        frm_btn.pack(fill="x", padx=10, pady=10)

        self.btn_compare = tk.Button(
            frm_btn, text="开始比对", command=self.on_compare_clicked
        )
        self.btn_compare.pack(side="left")

        # Result area
        tk.Label(self, text="结果:").pack(anchor="w", padx=10)
        self.txt_result = scrolledtext.ScrolledText(self, wrap="word")
        self.txt_result.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def browse_reference(self) -> None:
        path = filedialog.askopenfilename(
            title="选择标准文件 (MIDI/音频)",
            filetypes=[
                ("All supported", "*.mid *.midi *.wav *.mp3 *.flac *.ogg"),
                ("MIDI files", "*.mid *.midi"),
                ("Audio files", "*.wav *.mp3 *.flac *.ogg"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.entry_ref.delete(0, tk.END)
            self.entry_ref.insert(0, path)

    def browse_user(self) -> None:
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

    def on_compare_clicked(self) -> None:
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

        # Run comparison in a background thread to keep UI responsive
        thread = threading.Thread(
            target=self._run_compare, args=(ref_path, user_path), daemon=True
        )
        self.btn_compare.config(state="disabled", text="正在比对...")
        thread.start()

    def _run_compare(self, ref_path: Path, user_path: Path) -> None:
        try:
            self._append_result(f"加载标准文件: {ref_path}\n")
            ref_notes = load_notes_from_path(ref_path)
            self._append_result(f"标准音符数: {len(ref_notes)}\n")

            self._append_result(f"加载你的弹奏: {user_path}\n")
            user_notes = load_notes_from_path(user_path)
            self._append_result(f"你的音符数: {len(user_notes)}\n")

            if not ref_notes:
                self._append_result("标准文件没有检测到音符，无法比较。\n")
                return

            from audio_processing.comparator import compare_midi_note_sequences

            result = compare_midi_note_sequences(ref_notes, user_notes)

            lines = []
            lines.append("\n=== 比对结果 ===\n")
            lines.append(f"准确率: {result.accuracy:.3f}\n")
            lines.append(f"错误总数: {len(result.errors)}\n")
            for err in result.errors:
                etype = err["type"]
                t = err["time"]
                expected_name = err.get("expected_name")
                played_name = err.get("played_name")
                if etype == "wrong":
                    lines.append(
                        f"[{t:7.3f}s] 错音  期望={expected_name} 实际={played_name}\n"
                    )
                elif etype == "missed":
                    lines.append(
                        f"[{t:7.3f}s] 漏音  期望={expected_name}\n"
                    )
                elif etype == "extra":
                    lines.append(
                        f"[{t:7.3f}s] 多音  实际={played_name}\n"
                    )

            self._append_result("".join(lines))
        except Exception as exc:  # noqa: BLE001
            err_text = "".join(
                ["发生错误：", str(exc), "\n", traceback.format_exc(), "\n"]
            )
            self._append_result(err_text)
            messagebox.showerror("错误", f"比对过程中发生异常：\n{exc}")
        finally:
            # Restore button state
            self.btn_compare.config(state="normal", text="开始比对")

    def _append_result(self, text: str) -> None:
        def _inner() -> None:
            self.txt_result.insert(tk.END, text)
            self.txt_result.see(tk.END)

        # Ensure UI updates happen in main thread
        self.after(0, _inner)


def main() -> None:
    app = PianoTutorGUI()
    app.mainloop()


if __name__ == "__main__":
    main()

