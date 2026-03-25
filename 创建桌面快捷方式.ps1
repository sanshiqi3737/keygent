# 在桌面创建「Piano Tutor GUI」快捷方式（双击即启动，无黑框）
$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VbsPath = Join-Path $ProjectRoot "run_gui_launcher.vbs"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Piano Tutor GUI.lnk"

if (-not (Test-Path $VbsPath)) {
    Write-Host "未找到 run_gui_launcher.vbs，请确保在项目根目录运行本脚本。" -ForegroundColor Red
    exit 1
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$VbsPath`""
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "Piano Tutor - 钢琴陪练 GUI"
$Shortcut.Save()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null

Write-Host "已创建桌面快捷方式：$ShortcutPath" -ForegroundColor Green
Write-Host "双击「Piano Tutor GUI」即可启动（无黑框）。" -ForegroundColor Cyan
