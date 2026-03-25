@echo off
chcp 65001 >nul
echo 正在打包 PianoTutor 应用...
cd /d "%~dp0"

python -c "import PyInstaller" 2>nul || (
    echo 正在安装 PyInstaller...
    pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
)

pyinstaller --noconfirm --clean PianoTutor.spec

if exist "dist\PianoTutor\PianoTutor.exe" (
    echo.
    echo 打包完成。可执行程序在: dist\PianoTutor\PianoTutor.exe
    echo 若使用多声部模式，请将 CRNN_note_F1=0.9677_pedal_F1=0.9186.pth 放到 dist\PianoTutor\ 目录下。
    echo.
) else (
    echo 打包可能失败，请检查上方报错。
)
pause
