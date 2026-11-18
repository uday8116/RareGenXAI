#!/usr/bin/env bash
# Quick local sanity check, or full tests after downloading HPO.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ "$#" -gt 1 ]]; then
  echo "Usage: bash scripts/verify_local.sh [--quick|--full]" >&2
  exit 2
fi
mode="${1:---quick}"
if [[ "$mode" == "--help" || "$mode" == "-h" ]]; then
  echo "Usage: bash scripts/verify_local.sh [--quick|--full]"
  echo "--quick: doctor plus focused deterministic tests (no HPO download)."
  echo "--full: require validated HPO data, run all pytest tests."
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
