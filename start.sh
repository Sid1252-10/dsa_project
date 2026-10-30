#!/usr/bin/env bash
# ==============================================================================
# start.sh
# Sets up virtual environment, installs requirements, and launches
# both the Web UI server (frontend/API) and the backend simulator simultaneously.
# ==============================================================================

set -e

# Navigate to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================="
echo "   🚖 Cab Allocation System Startup Script"
echo "======================================================="

# 1. Detect working Python executable
if python --version &>/dev/null; then
    PYTHON_CMD="python"
elif python3 --version &>/dev/null; then
    PYTHON_CMD="python3"
elif py -3 --version &>/dev/null; then
    PYTHON_CMD="py -3"
else
    echo "[ERROR] Python is not installed or not in PATH."
    exit 1
fi

echo "[1/4] Using Python: $($PYTHON_CMD --version)"

# 2. Setup virtual environment if not already present
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[2/4] Creating virtual environment in '$VENV_DIR'..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
else
    echo "[2/4] Virtual environment found in '$VENV_DIR'."
fi

# Activate virtual environment (handles Linux/macOS and Windows Git Bash)
if [ -f "$VENV_DIR/Scripts/activate" ]; then
    # Windows
    # shellcheck disable=SC1091
    source "$VENV_DIR/Scripts/activate"
elif [ -f "$VENV_DIR/bin/activate" ]; then
    # Linux / macOS
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
else
    echo "[ERROR] Could not find virtual environment activation script."
    exit 1
fi

# 3. Install requirements
echo "[3/4] Installing dependencies from requirements.txt..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

# 4. Start servers
echo "[4/4] Starting backend and frontend simultaneously..."

# Clean up background web server when this script exits
cleanup() {
    echo ""
    if [ -n "${SERVER_PID:-}" ]; then
        echo "Shutting down web server (PID $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    echo "Goodbye!"
}
trap cleanup EXIT INT TERM

# Start Web UI Server (serves frontend client + Punjab map API) in background
export PORT=5174
python web/server/server.py &
SERVER_PID=$!

sleep 1

WEB_URL="http://localhost:5174"
echo ""
echo "-------------------------------------------------------"
echo "  🌐 Web UI (Frontend + API): $WEB_URL"
echo "-------------------------------------------------------"

# Try opening the browser automatically
if command -v start &>/dev/null; then
    start "$WEB_URL" 2>/dev/null || true
elif command -v cmd.exe &>/dev/null; then
    cmd.exe /c start "$WEB_URL" 2>/dev/null || true
elif command -v xdg-open &>/dev/null; then
    xdg-open "$WEB_URL" 2>/dev/null || true
elif command -v open &>/dev/null; then
    open "$WEB_URL" 2>/dev/null || true
fi

# Start the interactive CLI Backend Simulator in the foreground
python main.py
