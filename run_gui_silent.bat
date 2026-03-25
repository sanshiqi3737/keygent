@echo off
:: 无黑框启动 GUI：调用 VBS 静默执行
cd /d "%~dp0"
wscript "%~dp0run_gui_launcher.vbs"
