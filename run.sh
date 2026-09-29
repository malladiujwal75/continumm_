#!/usr/bin/env bash
# Local dev runner (Path A: Hindsight Cloud). Loads .env, installs deps
# into a venv if needed, starts the API + console UI on :8000.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

if [ -f .env ]; then
  set -a; source .env; set +a
else
  echo "No .env found — copy .env.example to .env and fill in HINDSIGHT_API_KEY first." >&2
  exit 1
fi

echo "Continuum starting on http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
