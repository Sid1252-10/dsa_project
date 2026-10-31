@echo off
setlocal
cd /d "%~dp0"

echo =======================================================
echo    Yarivo Startup (Windows)
echo =======================================================

set "PYTHON_CMD="
py -3 --version >nul 2>&1 && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    python --version >nul 2>&1 && set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    python3 --version >nul 2>&1 && set "PYTHON_CMD=python3"
)
if not defined PYTHON_CMD (
    echo [ERROR] Python 3 is not installed or not on PATH.
    pause
    exit /b 1
)

for /f "delims=" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%v"
echo Using %PY_VER%

set "VENV_DIR=%~dp0venv"
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto :error
)
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

echo Installing Python dependencies...
"%VENV_PYTHON%" -m pip install --quiet --upgrade pip
if errorlevel 1 goto :error
"%VENV_PYTHON%" -m pip install --quiet -r requirements.txt
if errorlevel 1 goto :error

set "PORT=5174"
set "WEB_URL=http://localhost:5174/index.html?build=landing-home-20261031"
start "Yarivo Web Server" /min "%VENV_PYTHON%" "%~dp0web\server\server.py"
if errorlevel 1 goto :error

timeout /t 2 /nobreak >nul
echo Yarivo dashboard: %WEB_URL%
start "" "%WEB_URL%"

echo Starting the Python CLI simulator. Close it or press Ctrl+C to stop both.
"%VENV_PYTHON%" main.py

echo.
echo Stopping Yarivo web server...
taskkill /fi "WINDOWTITLE eq Yarivo Web Server*" /t /f >nul 2>&1
echo Goodbye.
exit /b 0

:error
echo [ERROR] Yarivo startup failed. Check Python and pip setup.
taskkill /fi "WINDOWTITLE eq Yarivo Web Server*" /t /f >nul 2>&1
pause
exit /b 1
