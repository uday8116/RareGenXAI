#!/usr/bin/env bash
# Phase 1 local setup for Apple Silicon. Run from any working directory.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

prepare_data=0
for arg in "$@"; do
  case "$arg" in
    --data) prepare_data=1 ;;
    --help|-h)
      echo "Usage: bash scripts/bootstrap_macos.sh [--data]"
      echo "Creates .venv, installs requirements and runs the environment doctor."
      echo "--data additionally downloads official HPO source files (internet required)."
      exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This bootstrap script targets macOS. See docs/LOCAL_DEVELOPMENT_MACOS.md." >&2
  exit 1
fi
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "Notice: this Mac is not reporting arm64; installation may differ from Apple Silicon."
fi

PYTHON=""
for candidate in python3.11 python3.12; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done
if [[ -z "$PYTHON" ]]; then
  echo "Python 3.11 or 3.12 not found. Install: brew install python@3.11" >&2
  exit 1
fi
echo "Using $("$PYTHON" --version) ($("$PYTHON" -c 'import platform; print(platform.machine())'))"
if [[ ! -f ".venv/pyvenv.cfg" ]]; then
  "$PYTHON" -m venv .venv
fi
VENV_PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Virtual environment is invalid. Remove .venv and rerun." >&2
  exit 1
fi
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt
if [[ "$prepare_data" -eq 1 ]]; then
  "$VENV_PYTHON" -m src.data
  "$VENV_PYTHON" scripts/doctor.py --require-data
else
  "$VENV_PYTHON" scripts/doctor.py
fi
echo
echo "Setup complete. Next: bash scripts/verify_local.sh"
echo "Then launch: .venv/bin/python -m streamlit run app.py"
