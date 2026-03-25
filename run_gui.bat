@echo off
chcp 65001 >nul
set ROOT=%~dp0
cd /d "%ROOT%"

REM 查找 Python（py 优先，常见于 Windows）
set PY=py
py --version >nul 2>&1 || set PY=python
%PY% --version >nul 2>&1 || (
  echo 错误: 未找到 Python。请安装 Python 3.8+ 并加入 PATH。
  echo 下载: https://www.python.org/downloads/
  pause
  exit /b 1
)

echo ========== 检查依赖 ==========
%PY% -c "import librosa, pretty_midi" 2>nul || (
  echo 正在安装后端依赖...
  %PY% -m pip install -r backend\requirements.txt -q
  if errorlevel 1 (
    echo 依赖安装失败，请手动执行: %PY% -m pip install -r backend\requirements.txt
    pause
    exit /b 1
  )
)

echo.
echo ========== 启动 GUI ==========
cd backend
%PY% audio_compare_gui.py
if errorlevel 1 (
  echo.
  echo 启动失败，请检查上方错误信息。
)
pause
 