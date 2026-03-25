# 前后端一起运行（PowerShell）
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

Write-Host "========== 安装后端依赖 ==========" -ForegroundColor Cyan
& py -m pip install -r backend\requirements.txt -q
if ($LASTEXITCODE -ne 0) { & python -m pip install -r backend\requirements.txt -q }

Write-Host "`n========== 安装前端依赖 ==========" -ForegroundColor Cyan
Set-Location frontend
npm install
Set-Location $Root

Write-Host "`n========== 启动后端 (端口 8000) ==========" -ForegroundColor Green
Start-Process -FilePath "py" -ArgumentList "-m", "uvicorn", "backend.app:app", "--port", "8000" -WorkingDirectory $Root -WindowStyle Normal
Start-Sleep -Seconds 3

Write-Host "`n========== 启动前端 (端口 5173) ==========" -ForegroundColor Green
Write-Host "浏览器打开 http://localhost:5173" -ForegroundColor Yellow
Set-Location frontend
npm run dev
