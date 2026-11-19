#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -x .venv/bin/python ]]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi
echo "RareGenXAI local research API: http://127.0.0.1:8000/docs"
echo "No cloud hosting; no patient data. API bound to loopback only."
exec "$PYTHON" -m uvicorn src.api:app \
  --host 127.0.0.1 --port 8000 --no-access-log
