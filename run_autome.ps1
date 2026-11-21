Write-Host "Starting AutoMe (Backend, Frontend, and WhatsApp Service)..." -ForegroundColor Cyan

Start-Process cmd -ArgumentList '/k "title AutoMe Backend && cd /d C:\Users\Admin\Desktop\autome && python -m uvicorn backend.main:app --reload --port 8000"'
Start-Process cmd -ArgumentList '/k "title AutoMe Frontend && cd /d C:\Users\Admin\Desktop\autome\frontend && npm run dev"'
Start-Process cmd -ArgumentList '/k "title AutoMe WhatsApp && cd /d C:\Users\Admin\Desktop\autome\whatsapp-service && node index.js"'

Write-Host "`nAll AutoMe services are starting up in separate windows!" -ForegroundColor Green
Write-Host "- Backend:    http://127.0.0.1:8000"
Write-Host "- Frontend:   http://localhost:5173"
Write-Host "- WhatsApp:   http://localhost:3001"
