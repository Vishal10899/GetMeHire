# Launch FastAPI backend in production mode (No --reload, production ASGI settings)
Write-Host "Starting GetMeHire Backend in PRODUCTION mode on http://0.0.0.0:8000..." -ForegroundColor Green
Set-Location "$PSScriptRoot"
& "$PSScriptRoot\venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips "*"
