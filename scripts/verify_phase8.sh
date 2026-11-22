#!/usr/bin/env bash
# Phase 8: quick/offline checks are never mistaken for official full acceptance.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:---quick}"
if [[ "$MODE" != "--quick" && "$MODE" != "--full" ]]; then
  echo "Usage: bash scripts/verify_phase8.sh [--quick|--full]" >&2
  exit 2
fi
PYTHON=python3
if [[ -x .venv/bin/python ]]; then PYTHON=.venv/bin/python; fi
"$PYTHON" -m pytest -q tests/test_phase8_e2e.py tests/test_api.py tests/test_explainability.py
if [[ "$MODE" == "--quick" ]]; then
  echo "PASS: offline tests only. NOT full Phase 8 acceptance."
  exit 0
fi
if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
  echo "Missing Node.js/npm for full website verification" >&2; exit 1
fi
if [[ ! -d frontend/node_modules ]]; then
  echo "Missing frontend/node_modules. Run: cd frontend && npm install" >&2; exit 1
fi
"$PYTHON" -m src.verify_models --db data/local/raregen.sqlite3 --raw-dir data/raw
(cd frontend && npm run test:logic && npm run test && npm run build)
test -f frontend/dist/index.html
"$PYTHON" scripts/phase8_e2e.py --restart
echo "PASS: Phase 8 automated end-to-end and cold restart verification."
echo "Owner must still check live interaction on their Mac before final acceptance."
