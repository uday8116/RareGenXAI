#!/usr/bin/env bash
# Phase 10: release candidate validation, NEVER a clinical sign-off.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODE=--quick
if [[ $# -gt 0 ]]; then MODE="$1"; fi
if [[ "$MODE" != "--quick" && "$MODE" != "--full" ]]; then
  echo "Usage: bash scripts/verify_phase10.sh [--quick|--full]" >&2
  exit 2
fi
if [[ -x .venv/bin/python ]]; then PYTHON=.venv/bin/python
elif command -v python3 >/dev/null; then PYTHON=python3
else echo "Python 3 required" >&2; exit 1
fi
echo "=== Phase 10: isolated backup safety and documentation consistency ==="
"$PYTHON" -m pytest -q tests/test_phase10_backup.py tests/test_phase9_docs.py
"$PYTHON" -m py_compile scripts/phase10_backup.py tests/test_phase10_backup.py
echo "PASS offline checks. This is not the full research/system acceptance."
if [[ "$MODE" == "--quick" ]]; then exit 0; fi

echo "=== Phase 10: full upstream research integrity ==="
bash scripts/verify_phase7.sh --full
echo "=== Phase 10: full research website and clean two-cycle restart ==="
bash scripts/verify_phase8.sh --full
echo "=== Phase 10: backup and independent restore check ==="
RESEARCH_TMP="$(mktemp -d)"
trap 'rm -rf "$RESEARCH_TMP"' EXIT
"$PYTHON" scripts/phase10_backup.py create --root "$ROOT" \
  --out "$RESEARCH_TMP/research-backup.zip"
"$PYTHON" scripts/phase10_backup.py verify \
  --archive "$RESEARCH_TMP/research-backup.zip"
"$PYTHON" scripts/phase10_backup.py restore \
  --archive "$RESEARCH_TMP/research-backup.zip" \
  --destination "$RESEARCH_TMP/restored"
"$PYTHON" - "$RESEARCH_TMP/research-backup.zip" <<'PY'
import sys
from scripts.phase10_backup import verify
manifest = verify(sys.argv[1])
if manifest["missing_core"]:
    raise SystemExit("FAIL full release: missing core artifacts: " +
                     ", ".join(manifest["missing_core"]))
print("PASS: full core artifact backup verified and restored")
PY
echo "PASS automated release candidate checks on current local machine."
echo "STOP: human review, screenshots, supervisor sign-off and merge/tag still required."
