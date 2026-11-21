# AutoMe Desktop Launcher
# Checks if backend and WhatsApp microservice are already running before starting them

$backendRunning = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $backendRunning) {
    Start-Process cmd -ArgumentList '/c "cd /d C:\Users\Admin\Desktop\autome && python -m uvicorn backend.main:app --port 8000"' -WindowStyle Hidden
}

$whatsappRunning = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
if (-not $whatsappRunning) {
    Start-Process cmd -ArgumentList '/c "cd /d C:\Users\Admin\Desktop\autome\whatsapp-service && node index.js"' -WindowStyle Hidden
}

# Launch Electron Desktop Application
Set-Location "C:\Users\Admin\Desktop\autome\frontend"
if (Test-Path ".\node_modules\.bin\electron.cmd") {
    & ".\node_modules\.bin\electron.cmd" "electron\main.cjs"
} else {
    npx electron electron\main.cjs
}
