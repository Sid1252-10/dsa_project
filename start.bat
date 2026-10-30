@echo off
setlocal

cd /d "%~dp0"

echo =======================================================
echo    🚖 Cab Allocation System Startup Script (Windows)
echo =======================================================

:: 1. Detect Python executable
set "PYTHON_CMD="
py -3 --version >nul 2>&1 && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    python --version >nul 2>&1 && set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    python3 --version >nul 2>&1 && set "PYTHON_CMD=python3"
)

if not defined PYTHON_CMD (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

for /f "delims=" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%v"
echo [1/4] Using Python: %PY_VER%

:: 2. Setup virtual environment
set "VENV_DIR=venv"
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [2/4] Creating virtual environment in '%VENV_DIR%'...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
) else (
    echo [2/4] Virtual environment found in '%VENV_DIR%'.
)

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

:: 3. Install requirements
echo [3/4] Installing dependencies from requirements.txt...
"%VENV_PYTHON%" -m pip install --quiet --upgrade pip
"%VENV_PYTHON%" -m pip install --quiet -r requirements.txt

:: 4. Start servers
echo [4/4] Starting backend and frontend simultaneously...

set PORT=5174
set WEB_URL=http://localhost:5174

:: Start Web UI Server in background window titled WebUIServer
start "WebUIServer" /min "%VENV_PYTHON%" web\server\server.py

timeout /t 2 /nobreak >nul

echo.
echo -------------------------------------------------------
echo   🌐 Web UI (Frontend + API): %WEB_URL%
echo -------------------------------------------------------

:: Open default browser
start "" "%WEB_URL%"

:: Start interactive CLI Backend Simulator in foreground
"%VENV_PYTHON%" main.py

:: Cleanup background server upon exit
echo.
echo Shutting down web server...
taskkill /fi "WINDOWTITLE eq WebUIServer*" /t /f >nul 2>&1
echo Goodbye!

