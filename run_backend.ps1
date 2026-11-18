# Launch FastAPI backend from project root
Write-Host "Starting GetMeHire Backend on http://127.0.0.1:8000..." -ForegroundColor Green
Set-Location "$PSScriptRoot\backend"
& "$PSScriptRoot\backend\venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload
