#!/usr/bin/env bash
# Runs the backend (FastAPI/uvicorn) and frontend (Vite) together for local
# development. Ctrl+C stops both.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -d .venv ]; then
  echo "Error: .venv not found. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt" >&2
  exit 1
fi

if [ ! -d frontend/node_modules ]; then
  echo "Error: frontend/node_modules not found. Run: cd frontend && npm install" >&2
  exit 1
fi

cleanup() {
  echo
  echo "Stopping backend and frontend..."
  # uvicorn --reload and vite each spawn child processes that outlive their
  # direct PID on a plain `kill`, so free the ports instead of trusting PIDs.
  lsof -ti:8000 -sTCP:LISTEN | xargs -r kill 2>/dev/null || true
  lsof -ti:5173 -sTCP:LISTEN | xargs -r kill 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both."

wait
