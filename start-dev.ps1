# Start Jonche Platform Development Servers

$venv = "c:/Users/313jo/jonche-platform/.venv/Scripts/python.exe"
$projectRoot = "c:\Users\313jo\jonche-platform\jonche-platform"

Write-Host "🖤 Starting Jonche Platform Development Servers..." -ForegroundColor Magenta
Write-Host ""

# Start API Server
Write-Host "Starting API Server on port 5002..." -ForegroundColor Cyan
$env:API_PORT = 5002
$apiProc = Start-Process -NoNewWindow -PassThru -WorkingDirectory "$projectRoot\apps\api" -FilePath $venv -ArgumentList "app.py"
Start-Sleep -Seconds 2

# Start Web Server  
Write-Host "Starting Web Server on port 5005..." -ForegroundColor Cyan
$env:WEB_PORT = 5005
$env:API_BASE_URL = "http://localhost:5002/api"
$webProc = Start-Process -NoNewWindow -PassThru -WorkingDirectory "$projectRoot\apps\web" -FilePath $venv -ArgumentList "app.py"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "✅ Development servers started!" -ForegroundColor Green
Write-Host ""
Write-Host "Dashboard: http://localhost:5005" -ForegroundColor Yellow
Write-Host "API: http://localhost:5002" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop servers" -ForegroundColor Gray
Write-Host ""

# Keep the script running
$apiProc.WaitForExit()
$webProc.WaitForExit()
