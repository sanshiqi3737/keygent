#!/usr/bin/env python3
"""从项目根目录启动 GUI。自动在 backend 目录下运行。"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
SCRIPT = os.path.join(BACKEND, "audio_compare_gui.py")

if __name__ == "__main__":
    if not os.path.isfile(SCRIPT):
        print("错误: 未找到 backend/audio_compare_gui.py")
        sys.exit(1)
    os.chdir(BACKEND)
    sys.exit(subprocess.call([sys.executable, "audio_compare_gui.py"]))
