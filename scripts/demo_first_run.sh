#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/3] API tests"
cd "$ROOT/services/api"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt >/dev/null
.venv/bin/python -m pytest -q


echo "[2/3] Generate reliability evidence"
.venv/bin/python scripts/generate_reliability_evidence.py >/dev/null

echo "[3/3] Health endpoint check (requires API running on :8000)"
if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
  echo "API health OK"
else
  echo "API health check skipped/failing (start API to validate)."
fi

echo "Done. See evidence/reliability-evidence.json"
