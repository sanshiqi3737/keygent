@echo off
chcp 65001 >nul
set ROOT=%~dp0
cd /d "%ROOT%"

REM 查找 Python
set PY=py
py --version >nul 2>&1 || set PY=python
%PY% --version >nul 2>&1 || (
  echo 错误: 未找到 Python。请安装 Python 3.8+ 并加入 PATH。
  pause
  exit /b 1
)

echo ========== 检查后端依赖 ==========
%PY% -c "import uvicorn, fastapi" 2>nul || (
  echo 正在安装后端依赖...
  %PY% -m pip install -r backend\requirements.txt -q
  if errorlevel 1 (
    echo 后端依赖安装失败
    pause
    exit /b 1
  )
)

echo.
echo ========== 安装前端依赖 ==========
cd frontend
call npm install
if errorlevel 1 (
  echo 前端依赖安装失败
  pause
  exit /b 1
)
cd ..

echo.
echo ========== 启动后端 (端口 8000) ==========
start "PianoTutor-Backend" cmd /k "cd /d \"%ROOT%\" && %PY% -m uvicorn backend.app:app --port 8000"
timeout /t 3 /nobreak >nul

echo.
echo ========== 启动前端 (端口 5173) ==========
echo 浏览器将打开 http://localhost:5173
echo 关闭本窗口可停止前端；关闭「PianoTutor-Backend」窗口可停止后端。
echo.
cd frontend
npm run dev
