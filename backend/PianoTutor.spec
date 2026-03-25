# -*- mode: python ; coding: utf-8 -*-
# 在 backend 目录下执行: pyinstaller PianoTutor.spec
# 输出: dist/PianoTutor/PianoTutor.exe

import os

block_cipher = None

# 确保打包时能找到 backend 下的 audio_processing 包
spec_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['audio_compare_gui.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=[('使用说明.txt', '.')],
    hiddenimports=[
        'audio_processing',
        'audio_processing.midi_parser',
        'audio_processing.note_transcriber',
        'audio_processing.comparator',
        'librosa',
        'numpy',
        'scipy',
        'pretty_midi',
        'tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 若不打包多声部可减小体积（多声部需安装 piano_transcription_inference 后打包）
        # 'torch',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PianoTutor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 无黑框，纯 GUI
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='PianoTutor',
)
