# Launch FastAPI backend with Python 3.10.11 virtual environment
Write-Host "Starting GetMeHire Backend on http://127.0.0.1:8000..." -ForegroundColor Green
& "$PSScriptRoot\venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload
