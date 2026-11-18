#!/usr/bin/env bash
# Fast local sanity check; --full requires prepared HPO data.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mode="${1:---quick}"
if [[ "$mode" == "--help" || "$mode" == "-h" ]]; then
  echo "Usage: bash scripts/verify_local.sh [--quick|--full]"
  echo "--quick: doctor plus focused deterministic unit tests (no dataset download)."
  echo "--full: additionally require prepared HPO data and run the full pytest suite."
  exit 0
fi
if [[ "$mode" != "--quick" && "$mode" != "--full" ]]; then
  echo "Unknown mode: $mode" >&2
  exit 2
fi
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Missing .venv. Run bash scripts/bootstrap_macos.sh first." >&2
  exit 1
fi
PY="$ROOT/.venv/bin/python"
if [[ "$mode" == "--full" ]]; then
  "$PY" scripts/doctor.py --require-data
  "$PY" -m pytest -q
else
  "$PY" scripts/doctor.py
  "$PY" -m pytest -q tests/test_foundation.py tests/test_ranking.py tests/test_paired_stats.py
fi
echo "Local verification passed ($mode)."
