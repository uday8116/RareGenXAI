#!/usr/bin/env bash
# Phase 6 acceptance: a failure is never silently treated as "passed".
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:---quick}"

if [[ "$MODE" != "--quick" && "$MODE" != "--full" ]]; then
  echo "Usage: bash scripts/verify_phase6.sh [--quick|--full]" >&2
  exit 2
fi

if [[ -x .venv/bin/python ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Python 3.11 virtual environment is missing; run Phase 1 bootstrap." >&2
  exit 1
fi
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js 22 and npm are required for Phase 6 verification." >&2
  exit 1
fi
node -e 'const m=+process.versions.node.split(".")[0]; if (m !== 22) {console.error("Phase 6 requires Node 22");process.exit(1)}'

echo "=== Phase 6 Python core and FastAPI tests ==="
"$PYTHON_BIN" -m pytest -q tests/test_explainability.py tests/test_api.py

echo "=== Phase 5/6 dependency-free JavaScript checks ==="
(cd frontend && npm run test:logic)

if [[ "$MODE" == "--quick" ]]; then
  echo "Quick checks passed. This is NOT full Phase 6 acceptance."
  echo "For complete checks: bash scripts/verify_phase6.sh --full"
  exit 0
fi

echo "=== Strict official HPO and trained model integration ==="
RAREGEN_REQUIRE_PHASE6_INTEGRATION=1 \
  "$PYTHON_BIN" -m pytest -q tests/test_phase6_integration.py

if [[ ! -d frontend/node_modules ]]; then
  echo "Missing React test/build dependencies. Run: cd frontend && npm install" >&2
  exit 1
fi

echo "=== React interaction tests ==="
(cd frontend && npm run test)
echo "=== Production Vite build ==="
(cd frontend && npm run build)
test -f frontend/dist/index.html
test -d frontend/dist/assets
echo "All automated Phase 6 acceptance checks passed."
echo "Manual browser review on the actual Apple M5 is still required."
