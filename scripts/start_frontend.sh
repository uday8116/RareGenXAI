#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../frontend"
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js 22 and npm are required. Install them first." >&2
  exit 1
fi
if [[ ! -d node_modules ]]; then
  echo "Dependencies missing: cd frontend && npm install" >&2
  exit 1
fi
echo "RareGenXAI research UI at http://127.0.0.1:5173"
echo "Start FastAPI separately: bash scripts/start_api.sh"
exec npm run dev
