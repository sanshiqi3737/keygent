' 无黑框启动 Piano Tutor GUI（静默运行）
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strRoot = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strRoot

' 查找 Python：py 优先
pyCmd = "py"
exitCode = WshShell.Run("cmd /c py --version", 0, True)
If exitCode <> 0 Then pyCmd = "python"

' 检查依赖，缺失时才安装（避免每次启动都联网）
exitCode = WshShell.Run("cmd /c " & pyCmd & " -c ""import librosa, pretty_midi""", 0, True)
If exitCode <> 0 Then
  WshShell.Run "cmd /c " & pyCmd & " -m pip install -r " & Chr(34) & strRoot & "\backend\requirements.txt" & Chr(34) & " -q", 0, True
End If

' 在 backend 目录启动 GUI（1 = 正常显示窗口）
WshShell.CurrentDirectory = strRoot & "\backend"
WshShell.Run pyCmd & " audio_compare_gui.py", 1, False
