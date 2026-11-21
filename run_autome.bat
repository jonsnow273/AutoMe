@echo off
echo Starting AutoMe (Backend, Frontend, and WhatsApp Service)...

start "AutoMe Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --reload --port 8000"
start "AutoMe Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
start "AutoMe WhatsApp" cmd /k "cd /d %~dp0whatsapp-service && node index.js"

echo All AutoMe services are starting up!
echo - Backend:    http://127.0.0.1:8000
echo - Frontend:   http://localhost:5173
echo - WhatsApp:   http://localhost:3001
pause
