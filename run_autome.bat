@echo off
echo Starting AutoMe Backend and Frontend...

start "AutoMe Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --reload --port 8000"
start "AutoMe Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo AutoMe is starting up!
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:5173
pause
