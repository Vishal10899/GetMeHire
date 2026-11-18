@echo off
echo Starting GetMeHire Backend on http://127.0.0.1:8000...
cd /d "%~dp0backend"
"%~dp0backend\venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload
