# RareGenXAI v0.10.0-rc1 — Proposed research release notes

**NOT RELEASED OR TAGGED.** These draft notes explain what the eventual local
research release candidate would contain, conditional on Phase 10 acceptance.

## Scope

- Source-verified HPO knowledge in local SQLite schema v2.
- Overlap and semantic ranking; TF-IDF retrieval and experimental logistic,
  random forest, XGBoost and MLP rerankers.
- Local FastAPI and React frontend, evidence displays and strict HPO validation.
- Phase 7 preregistered research audits and *historical* RareBench reanalysis;
  Phase 8 system verification and Phase 9 academic drafting materials.
- Phase 10 allowlisted research backup tool and SHA-256 integrity verification.

## Results with proper evidence

An older six-method archive contained 178 eligible published RareBench cases.
Exact-overlap Top-1 was 37.64% and Top-5 was 54.49%; XGBoost Top-1 was
36.52%. These are saved earlier predictions, **not fresh Phase 7 inference**
or clinically validated accuracy. See `docs/PHASE_07_HISTORICAL_REANALYSIS.md`
and `docs/PHASE_09_EVIDENCE_LEDGER.md`. No matched DeepRare case output.

## Environment and restrictions

The local project targets macOS Apple Silicon with Python 3.11 and Node 22.
It is research only, not a medical device or a public web service. Downloaded
HPO knowledge and joblib binaries are excluded from Git and any proposed public
release. Only load model files from an established trusted source.

## Unresolved for final release

Actual working GitHub Actions runs, Phase 7 new benchmark, Phase 8 Mac full
integration/restart, Phase 9 supervisor/campus approval, real screenshots,
backup-restore drill, correct stacked PR merges, and explicit tag approval.
No release tag is created in the Phase 10 PR.
