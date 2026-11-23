#!/usr/bin/env bash
# Phase 7: locally verified, pre-registered research-evaluation run.
# Never claim a passed real-case experiment unless both evaluator and auditor succeed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:---quick}"
if [[ "$MODE" != "--quick" && "$MODE" != "--full" ]]; then
  echo "Usage: bash scripts/verify_phase7.sh [--quick|--full]" >&2
  exit 2
fi
if [[ -x .venv/bin/python ]]; then
  PYTHON=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "Missing Python 3.11+ (or local .venv). Complete Phase 1 bootstrap." >&2
  exit 1
fi

echo "=== Phase 7: deterministic fixture and tamper-rejection tests ==="
"$PYTHON" -m pytest -q tests/test_phase7_experiments.py tests/test_phase7_historical_reaudit.py
if [[ "$MODE" == "--quick" ]]; then
  echo "Phase 7 core tests passed; official patient cohort was NOT evaluated."
  exit 0
fi

echo "=== Phase 7: preflight official model and case provenance ==="
for file in \
  data/external/rarebench_cases.csv \
  data/external/rarebench_manifest.json \
  data/raw/manifest.json \
  data/local/raregen.sqlite3 \
  models/raregen_ml.joblib \
  models/raregen_ml.manifest.json; do
  if [[ ! -f "$file" ]]; then
    echo "Cannot run full Phase 7: missing required real artifact $file" >&2
    echo "Prepare official HPO/model from Phases 2–3; run python -m src.rarebench --limit-per-subset 100000." >&2
    exit 1
  fi
done
"$PYTHON" -m src.verify_models --db data/local/raregen.sqlite3 --raw-dir data/raw

PLAN=results/phase7_plan.json
if [[ -e "$PLAN" ]]; then
  echo "A frozen protocol already exists: $PLAN" >&2
  echo "Keep it for an audit of the original run, or archive it before a NEW experiment." >&2
  exit 1
fi
mkdir -p results

echo "=== Freeze source, case set, model and methods BEFORE ranking ==="
"$PYTHON" -m src.phase7_experiments freeze \
  --cases data/external/rarebench_cases.csv \
  --dataset-manifest data/external/rarebench_manifest.json \
  --model-manifest models/raregen_ml.manifest.json \
  --model models/raregen_ml.joblib \
  --methods tfidf logistic random_forest xgboost mlp overlap \
  --retrieval-k 40 --seed 42 --out "$PLAN"

echo "=== Evaluate every eligible published external case with the frozen methods ==="
"$PYTHON" -m src.evaluate_external \
  --cases data/external/rarebench_cases.csv \
  --model models/raregen_ml.joblib \
  --methods tfidf logistic random_forest xgboost mlp overlap \
  --retrieval-k 40 --phase7-plan "$PLAN" --out results/external_case_results.csv

echo "=== Audit case-method alignment, metrics, paired intervals and errors ==="
"$PYTHON" -m src.phase7_experiments audit \
  --cases data/external/rarebench_cases.csv \
  --dataset-manifest data/external/rarebench_manifest.json \
  --model-manifest models/raregen_ml.manifest.json \
  --model models/raregen_ml.joblib \
  --plan "$PLAN" \
  --results results/external_case_results.csv \
  --legacy-summary results/external_cohort_summary.csv \
  --replicates 2000 --verify-model-membership --out-dir results

echo "Phase 7 real external cohort audit passed. This is retrospective, not clinical validation."
echo "Inspect results/phase7_provenance.json and all cohort/error CSVs before making claims."
