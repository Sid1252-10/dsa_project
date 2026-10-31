#!/usr/bin/env bash
# Start the Yarivo web app/API and the Python CLI simulator.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=(python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD=(python)
elif command -v py >/dev/null 2>&1; then
  PYTHON_CMD=(py -3)
else
  echo "[ERROR] Python 3 is not installed or not on PATH."
  exit 1
fi

echo "Using $(${PYTHON_CMD[@]} --version)"

VENV_DIR="$SCRIPT_DIR/venv"
if [[ ! -x "$VENV_DIR/bin/python" && ! -x "$VENV_DIR/Scripts/python.exe" ]]; then
  echo "Creating virtual environment..."
  "${PYTHON_CMD[@]}" -m venv "$VENV_DIR"
fi

if [[ -x "$VENV_DIR/bin/python" ]]; then
  VENV_PYTHON="$VENV_DIR/bin/python"
else
  VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
fi

echo "Installing Python dependencies..."
"$VENV_PYTHON" -m pip install --quiet --upgrade pip
"$VENV_PYTHON" -m pip install --quiet -r requirements.txt

export PORT=5174
"$VENV_PYTHON" web/server/server.py &
SERVER_PID=$!

cleanup() {
  echo
  echo "Stopping Yarivo web server..."
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

WEB_URL="http://localhost:5174/index.html?build=landing-home-20261031"
for _ in {1..20}; do
  if curl --silent --fail "http://localhost:5174/api/graph" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

echo "Yarivo dashboard: $WEB_URL"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$WEB_URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open "$WEB_URL" >/dev/null 2>&1 || true
elif command -v cmd.exe >/dev/null 2>&1; then
  cmd.exe /c start "" "$WEB_URL" >/dev/null 2>&1 || true
fi

echo "Starting the Python CLI simulator. Press Ctrl+C to stop both."
"$VENV_PYTHON" main.py
