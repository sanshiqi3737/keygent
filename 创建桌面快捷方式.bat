@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在创建桌面快捷方式「Piano Tutor GUI」...
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0创建桌面快捷方式.ps1"
if errorlevel 1 (
  echo 创建失败，请检查 PowerShell 是否可用。
) else (
  echo.
  echo 完成。请到桌面双击「Piano Tutor GUI」启动（无黑框）。
)
pause
