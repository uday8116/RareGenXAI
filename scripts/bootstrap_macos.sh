#!/usr/bin/env bash
# Phase 1 native Apple Silicon bootstrap. No sudo, no hosting, no model training.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

prepare_data=0
for arg in "$@"; do
  case "$arg" in
    --data) prepare_data=1 ;;
    --help|-h)
      echo "Usage: bash scripts/bootstrap_macos.sh [--data]"
      echo "Creates a Python 3.11/3.12 .venv, installs requirements, records local versions."
      echo "--data also downloads official HPO research files (internet required)."
      exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script targets macOS; see docs/LOCAL_DEVELOPMENT_MACOS.md." >&2
  exit 1
fi
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "Apple Silicon native arm64 Terminal required; disable Rosetta for Terminal." >&2
  exit 1
fi

PYTHON=""
for candidate in python3.11 python3.12; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if [[ "$("$candidate" -c 'import platform; print(platform.machine())')" == "arm64" ]]; then
      PYTHON="$candidate"
      break
    fi
  fi
done
if [[ -z "$PYTHON" ]]; then
  echo "Native arm64 Python 3.11 or 3.12 not found. Try: brew install python@3.11" >&2
  exit 1
fi
echo "Using $("$PYTHON" --version) (arm64)"

if [[ ! -f ".venv/pyvenv.cfg" ]]; then
  "$PYTHON" -m venv .venv
fi
VENV_PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Invalid .venv; see environment reset instructions in the macOS guide." >&2
  exit 1
fi
if ! "$VENV_PYTHON" -c 'import platform,sys
assert sys.prefix != sys.base_prefix
assert (3,11) <= sys.version_info[:2] <= (3,12)
assert platform.machine() == "arm64"
'; then
  echo "Existing .venv has an unsupported version or architecture." >&2
  echo "Back up needed files, remove only .venv, then rerun bootstrap." >&2
  exit 1
fi
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt
# Local snapshot of the exact resolved versions; ignored by Git.
"$VENV_PYTHON" -m pip freeze --local > environment-local.txt
if [[ "$prepare_data" -eq 1 ]]; then
  "$VENV_PYTHON" -m src.data
  "$VENV_PYTHON" scripts/doctor.py --require-data
else
  "$VENV_PYTHON" scripts/doctor.py
fi
echo
echo "Environment prepared. Saved local dependencies in environment-local.txt"
echo "Next: bash scripts/verify_local.sh"
echo "Launch current app: .venv/bin/python -m streamlit run app.py"
