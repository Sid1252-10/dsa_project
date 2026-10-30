@echo off
setlocal

cd /d "%~dp0"

echo =======================================================
echo    Cab Allocation System Startup Script (Windows)
echo =======================================================

:: 1. Detect Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

:: 2. Setup venv
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

:: 3. Install requirements
echo [2/3] Installing requirements...
venv\Scripts\python.exe -m pip install --quiet -r requirements.txt

:: 4. Start Web UI in background and CLI in foreground
echo [3/3] Starting backend and frontend...
set PORT=5174
start "" /b venv\Scripts\python.exe web\server\server.py
timeout /t 2 /nobreak >nul
start http://localhost:5174

venv\Scripts\python.exe main.py
