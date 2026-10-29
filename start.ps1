# ==============================================================================
# start.ps1
# Windows PowerShell startup script.
# Sets up virtual environment, installs requirements, and launches
# both the Web UI server (frontend/API) and the backend simulator simultaneously.
# ==============================================================================

$ErrorActionPreference = "Stop"

# Navigate to script directory
Set-Location -Path $PSScriptRoot

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   🚖 Cab Allocation System Startup Script (PowerShell)" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# 1. Detect Python
$pythonCmd = "python"
try {
    $pyVer = & python --version 2>&1
    Write-Host "[1/4] Using Python: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed or not found in PATH." -ForegroundColor Red
    exit 1
}

# 2. Setup virtual environment
$venvPath = Join-Path $PSScriptRoot "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "[2/4] Creating virtual environment in 'venv'..." -ForegroundColor Yellow
    & python -m venv venv
} else {
    Write-Host "[2/4] Virtual environment found in 'venv'." -ForegroundColor Green
}

# Python and Pip paths inside venv
$venvPython = Join-Path $venvPath "Scripts\python.exe"

# 3. Install requirements
Write-Host "[3/4] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet -r requirements.txt

# 4. Start servers
Write-Host "[4/4] Starting backend and frontend simultaneously..." -ForegroundColor Yellow

# Start Web UI Server as background process
$webScript = Join-Path $PSScriptRoot "web\server\server.py"
$env:PORT = "5174"
$serverProc = Start-Process -FilePath $venvPython -ArgumentList "`"$webScript`"" -PassThru -NoNewWindow

Start-Sleep -Seconds 1

$webUrl = "http://localhost:5174"
Write-Host ""
Write-Host "-------------------------------------------------------" -ForegroundColor Cyan
Write-Host "  🌐 Web UI (Frontend + API): $webUrl" -ForegroundColor Cyan
Write-Host "-------------------------------------------------------" -ForegroundColor Cyan

# Open default browser
try {
    Start-Process $webUrl
} catch {}

# Start interactive CLI simulator in foreground and clean up when done
try {
    $mainScript = Join-Path $PSScriptRoot "main.py"
    & $venvPython "$mainScript"
} finally {
    Write-Host ""
    Write-Host "Shutting down web server..." -ForegroundColor Yellow
    if ($serverProc -and -not $serverProc.HasExited) {
        Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Goodbye!" -ForegroundColor Green
}
