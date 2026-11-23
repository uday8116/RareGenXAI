# RareGenXAI — Release candidate handover (unverified)

**Source status:** Phases 1–10 are integrated into private GitHub `main` (2026-11-23). The source snapshot was merged through [PR #14](https://github.com/uday8116/RareGenXAI/pull/14), including Phase 4 API security protections and Phases 5–10 application/research code. The previous superseded stacked PRs were closed without separately merging each PR.

**This is a source handover, not a verified software release.** At the owner's request, tests were not performed in this update. Previously GitHub Actions jobs failed before executing steps. No latest-commit passing run, Mac end-to-end demonstration, official HPO/model artifact audit, clinical evaluation or university supervisor sign-off has been established.

## Included

React/Vite research interface, local-only FastAPI backend, HPO SQLite schema and importer, ontology-aware baselines, TF-IDF and experimental rerankers, XAI displays, research experiment and audit code, Phase 9 draft academic materials, Phase 10 local backup/restore tool and guidance.

## Data distribution

The project does **not** bundle `data/local/raregen.sqlite3`, `data/raw/` official ontology/annotation files, `models/raregen_ml.joblib` or model manifests. They are private local artifacts created on the owner’s Mac from documented official data/training commands. Do not expose a backup or deserialize a model from an untrusted source.

## Research result disclosure

The archived six-method RareBench snapshot covers 178 eligible previously saved cases. The exact-overlap baseline had Top-1 37.64% and Top-5 54.49% in that snapshot. These results have not been re-inferred in the present handover, and do not demonstrate clinical accuracy. See `docs/PHASE_09_EVIDENCE_LEDGER.md`.

## Status

- Code integrated: **yes**.
- Production/clinical release: **no**.
- Tests: **deliberately skipped by owner instruction**.
- Local database/model verified: **no**.
- Academic approvals: **pending**.
- GitHub tag and published release: **not created**.
- Detailed inventory and handover steps: `docs/RELEASE_HANDOVER_NO_TESTING.md`.

Research prototype only; not for clinical diagnosis.
