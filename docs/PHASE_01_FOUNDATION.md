# Phase 01 — Repository audit, environment and reproducibility

**Target machine:** Apple M5, 16 GB unified memory, macOS arm64.
**Code baseline:** `main` at `3fd3c9c8b8325a508cfd59724662fdcc4d277f8a`.
**Research scope:** offline-capable, local-only prototype. Never present research rankings as medical diagnoses.

## 1. Audit findings (source reviewed, not a new experimental run)

| Area | Code already found | Reality / gap |
| --- | --- | --- |
| Application | `app.py` | Basic Streamlit interface only, no React UI or FastAPI endpoints |
| Knowledge source | `src/data.py` | Downloads HPO ontology and HPOA; raw data generated locally, not stored in Git |
| Semantic ranking | `src/ranking.py` | Overlap and semantic scoring with phenotype contributions |
| ML | `src/ml.py`, `src/train_ml.py` | TF-IDF, logistic regression, random forest, XGBoost, MLP; fitted artifacts are not committed |
| GNN | `src/gnn.py`, `src/evaluate_gnn.py` | Experimental graph reranker, not integrated into the Streamlit model menu or persisted |
| External cases | `src/rarebench.py`, `src/evaluate_external.py` | Published RareBench evaluation scripts; not prospective clinical validation |
| Statistics | `src/paired_stats.py` | Exploratory case-level paired bootstrap method |
| Tests | `tests/` and `.github/workflows/tests.yml` | Unit/integration workflow; integration test depends on prepared HPO |
| Database | Generated JSON, CSV | No structured application database or migrations yet |
| Documentation | `docs/` | Existing reports must be reconciled with current experiments |

The existing `main` CI completed successfully: https://github.com/uday8116/RareGenXAI/actions/runs/43495432833. A previous separate PR improves matched-case CSV validation: https://github.com/uday8116/RareGenXAI/pull/1. These do not prove that the new M5 laptop is configured.

## 2. Known research evidence and limits

Repository reports 178 eligible retrospective RareBench cases (LIRICAL 143, MME 11, HMS 24). The documented exact-overlap baseline has 37.64% Top-1 / 54.49% Top-5; ML and experimental GNN methods did not exceed it overall. See `docs/VERIFIED_EXTERNAL_RESULTS.md`, `docs/XGBOOST_MLP_EXTERNAL_RESULTS.md`, and `docs/GNN_FULL_BENCHMARK_RESULTS.md`.

These numbers have **not** been reproduced locally by this Phase 1 change. Models are trained using synthetic phenotype samples generated from HPO disease annotations, not independently obtained clinical patient training data. A genuine identical-case DeepRare run is still missing. Do not claim clinical validity, calibrated probabilities, or superiority over DeepRare.

## 3. Audit risks to address in later phases

1. **Schema drift:** `src/data.py` expects specific HPOA field names. Validate against a downloaded, versioned release and fail clearly on incompatible schemas (Phase 2).
2. **Version reproducibility:** `requirements.txt` uses ranges rather than a platform lock. Record exact installed versions with `.venv/bin/python -m pip freeze > environment-local.txt` (do not commit machine-specific output) and consider a controlled lock once stack selection is finalized (Phase 2).
3. **Case parsing:** test string-form HPO inputs and disease identifiers in `src/rarebench.py` before regenerating benchmarks (Phase 2/3).
4. **Benchmark leakage:** synthetic training originates from the same disease annotation knowledge base used in retrieval; hold out appropriate development data and report literature overlap risk (Phase 3/7).
5. **Model packaging:** fit/persist/load-check complete models, metadata, and preprocessing before exposing inference through a new API (Phase 3/4).
6. **Performance:** full ontology similarity is potentially expensive; profile before promising instant inference in the new UI (Phase 3/5).
7. **Scientific documentation consistency:** earlier notes may predate completed benchmarks; update outdated statements before the dissertation (Phase 9).
8. **Privacy and clinical safety:** use public de-identified or synthetic inputs, local storage by default, clear research-only warnings throughout.

## 4. Phase 1 implementation scope

- `.python-version` recommends Python 3.11.
- `scripts/bootstrap_macos.sh` creates `.venv`, installs dependencies and optionally prepares HPO.
- `scripts/doctor.py` checks native architecture, importable dependencies (not just presence), raw HPO checksums/schema, parsed profiles and saved model-file presence.
- `scripts/verify_local.sh` provides reproducible quick/full tests.
- `tests/test_foundation.py` exercises the environment checker without external datasets.
- `.github/workflows/foundation.yml` checks Python/shell syntax on Linux and Apple Silicon runners **and actually installs dependencies and runs quick checks on macOS arm64**.
- `docs/LOCAL_DEVELOPMENT_MACOS.md` has user instructions.
- `docs/PROJECT_IMPLEMENTATION_ROADMAP.md` defines future phase gates.

Phase 1 intentionally does **not** claim a finished new UI, new database, new trained model or results.

## 5. Acceptance criteria / evidence

| Gate | Success definition | Verification |
| --- | --- | --- |
| P1-A | Source audit and unresolved risks written down | This document |
| P1-B | macOS bootstrap operates without sudo and only uses `.venv` | Run on target Mac |
| P1-C | CLI reports actionable errors for unsupported Python, Rosetta and invalid/missing HPO inputs | `tests/test_foundation.py` |
| P1-D | Quick tests succeed without HPO downloads | `bash scripts/verify_local.sh` on target Mac |
| P1-E | CI validates scripts and actually bootstraps a macOS arm64 runner | New foundation workflow run |
| P1-F | Full existing prototype can load from real HPO data | `--data`, `--full`, manual local Streamlit test |
| P1-G | New files reviewed and merged without disrupting `main` | Phase 1 pull request |

**Status is evidence-based:** a GitHub CI green light verifies CI runners; P1-B, P1-D and P1-F still require executing the documented commands on the user's physical Mac.

## 6. Phase 2 handoff

Design a local SQLite schema with stable IDs, foreign keys and migrations; ingest versioned official HPO and HPOA, verify provenance/checksums, validate referential integrity and expose a read-only data-access layer. Do not yet add patient-identifiable storage or run unapproved clinical datasets.

## 7. Phase 1 follow-up audit and changes

The first CI run was green, but the audit found that the doctor only verified data file presence and the workflow checked macOS shell syntax without executing a native install. This branch now adds streaming SHA-256 checks against the downloaded manifest, HPOA/JSON structure checks, native arm64 and virtualenv preflight, actual Python module imports, version snapshot ignored by Git, deterministic tests for corrupted data, and a macOS arm64 bootstrap CI job. Local data, generated SQLite files and the machine-specific dependency snapshot are excluded from Git.

These checks verify an environment and **data packaging integrity**, not medical annotation correctness, calibrated model scores, or independent clinical validation. The final user-machine verification gates remain the owner's responsibility, because GitHub cannot inspect or operate their physical Mac.

### Native macOS bootstrap failure discovered during review

The expanded macOS arm64 CI initially failed during the real bootstrap: importing XGBoost raised `XGBoostError: libomp.dylib could not be loaded`. This is a missing Homebrew OpenMP runtime, not a Python installation error. The bootstrap now checks for the native `/opt/homebrew/opt/libomp/lib/libomp.dylib` and visibly installs `libomp` through Homebrew when necessary. The macOS CI job exercises this exact path. Verify the latest CI run before marking the issue fixed.
