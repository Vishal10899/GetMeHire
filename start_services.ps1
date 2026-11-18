# PowerShell startup script for Global Job Discovery Platform (GetMeHire)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   GetMeHire Job Discovery Platform — Startup Script" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start FastAPI Backend with Python 3.10.11 virtual environment
Write-Host "`n[1/2] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
$BackendProcess = Start-Process -FilePath "D:\24JObs\backend\venv\Scripts\uvicorn.exe" `
    -ArgumentList "app.main:app --host 0.0.0.0 --port 8000 --reload" `
    -WorkingDirectory "D:\24JObs\backend" `
    -PassThru

# Wait for backend readiness
Write-Host "Waiting for backend to be ready..." -ForegroundColor Gray
$Ready = $false
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($res.status -eq "healthy") {
            $Ready = $true
            break
        }
    } catch {
        # continue waiting
    }
}

if ($Ready) {
    Write-Host "Backend is healthy and accepting connections." -ForegroundColor Green
} else {
    Write-Host "Warning: Backend startup taking longer than expected. Continuing with frontend..." -ForegroundColor Yellow
}

# 2. Start Next.js Frontend
Write-Host "`n[2/2] Starting Next.js Frontend on http://localhost:3000..." -ForegroundColor Green
$FrontendProcess = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run dev" `
    -WorkingDirectory "D:\24JObs\frontend" `
    -PassThru

Write-Host "`nAll platform services launched!" -ForegroundColor Green
Write-Host "• Frontend UI:    http://localhost:3000" -ForegroundColor Yellow
Write-Host "• Backend API:   http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "• OpenAPI Docs:  http://127.0.0.1:8000/api/docs" -ForegroundColor Yellow
Write-Host "`nDemo Accounts Available:" -ForegroundColor White
Write-Host "  Candidate: candidate@example.com / Candidate@123456"
Write-Host "  Admin:     admin@jobplatform.com / Admin@123456"
