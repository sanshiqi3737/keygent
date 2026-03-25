# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller：生成 dist_py/piano-backend/（onedir），内含 piano-backend.exe + _internal。
构建（在项目根目录执行）：
  py -m pip install -r backend/requirements.txt pyinstaller
  py -m PyInstaller --clean --noconfirm --distpath dist_py --workpath build_py desktop/pyinstaller/piano-backend.spec
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# PyInstaller 用 exec 跑 spec，没有 __file__；用其注入的 SPEC（本 spec 的绝对路径）
# spec 在 desktop/pyinstaller/：向上三级 = 仓库根
ROOT = Path(SPEC).resolve().parent.parent.parent

m_datas, m_binaries, m_hidden = collect_all("music21")

datas = [(str(ROOT / "frontend" / "dist"), "frontend/dist")]
_env = ROOT / ".env.example"
if _env.exists():
    datas.append((str(_env), "."))

launcher = str(ROOT / "piano_backend_launcher.py")

hiddenimports = list(m_hidden) + [
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "pydantic.deprecated.decorator",
]

a = Analysis(
    [launcher],
    pathex=[str(ROOT)],
    binaries=m_binaries,
    datas=datas + m_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="piano-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="piano-backend",
)
