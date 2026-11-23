# RareGenXAI — v0.10.0-rc1 unverified handover snapshot

**Status: source-integrated, UNTESTED, NOT A PUBLISHED RELEASE.**

**Freeze reference:** main source commit `ad53ece83beedadf3bf4cd31d511cfdafb61795e` (all phases integrated via PR #14 on 2026-11-23). This document update will produce a newer docs-only commit on main. Use the latest main commit for current docs, or the frozen source commit to reproduce the original code snapshot.

**User instruction:** no testing. No automated tests, full external research evaluation, browser smoke checks, database existence checks, or backup recovery drills were performed during this handover update. Do not infer success from GitHub commit/merge status.

## Supplied in private GitHub repository

1. Python FastAPI backend, loopback-only security policy, HPO validation, and ranked candidate explanations.
2. React/Vite research website and dashboards.
3. SQLite schema-v2 migration/importer and official HPO downloader.
4. Baseline and experimental ML ranking implementations, verified-source logic and training scripts.
5. Phase 7 evaluation scripts, archived historical retrospective metrics and source-context caveats.
6. Phase 8 verification scripts; Phase 9 dissertation, 12-slide source, viva notes, evidence ledger.
7. Phase 10 allowlisted backup/restore tool, release recipes, safety documents and regression tests (not executed on this request).
8. Git history and already merged Phase 4/5 and Phase 6–10 integration. Stacked PRs #10–#13 were closed **superseded**, not merged independently, because their commits are ancestors of main.

## What is not in GitHub

The **actual** local database `data/local/raregen.sqlite3`, official HPO raw downloads under `data/raw/`, the trained model `models/raregen_ml.joblib` and associated manifest are intentionally Git-ignored. No evidence was provided that these exist on the owner's Mac. There is no cloud database or public deployment. These should not be uploaded to an ordinary public release.

## Exact non-testing handover instructions

In the local RareGenXAI repository, synchronize code:

```bash
git switch main
git pull --ff-only origin main
```

For optional creation of database **only if it does not exist**, after Python dependencies are installed:

```bash
python -m src.data
python -m src.knowledge_db build
```

The database-builder command will refuse to replace an existing SQLite file unless explicitly told to; **do not use `--replace` without backing up the original**. Model training is separate and may be CPU/time intensive; it has not been executed as part of this handover. The database is knowledge about HPO phenotypes and rare diseases, **not patient records**.

The owner can create a local research backup, without sending its bytes to GitHub:

```bash
python scripts/phase10_backup.py create --out ~/RareGenXAI-research-backup.zip
```

This creates a ZIP of *existing allowlisted research files*; it records missing source/model files rather than fabricating them. For an accepted handover, keep the archive private/encrypted and use the verify/restore instructions in `docs/PHASE_10_RELEASE_HANDOVER.md` when testing is permitted. No actual backup has been created in this request.

## Final academic preparation

- Technical dissertation working draft: `docs/PHASE_09_DISSERTATION_DRAFT.md`.
- Source for 12-slide viva presentation: `docs/PHASE_09_PRESENTATION.md`.
- Explanation script and 25 viva questions: `docs/PHASE_09_SPEECH_AND_VIVA.md`.
- Snapshot reconciliation: `docs/PHASE_09_EVIDENCE_LEDGER.md`.
- University-specific cover pages, signatures, supervisor decisions and genuine live screenshots require the owner's institution and computer; none has been fabricated.

## Explicit unresolved blockers / known limitations

- **Tests are intentionally skipped.** No claim of a passing latest commit, a functional local website, successful model loading, or completed end-to-end clinical-case evaluation.
- The earlier archived 178-case RareBench results are saved retrospective predictions, not a new verified run. No matched-case DeepRare victory or prospective clinical performance established.
- No clinical diagnosis, medical device status, hospital integration, protected patient-data intake or public hosting.
- Research rankings are hypotheses, not probabilities. Retrieved ML candidates and overlap baseline need not share exactly the same candidate universe.
- Official campus/supervisor approval and authenticated GitHub Release/tag do not exist.
- Only source is fully integrated; private local DB/model data must be prepared on the owner's machine.

## Release labeling rule

Call this an **UNVERIFIED RESEARCH HANDOVER SNAPSHOT**. If testing is knowingly waived, avoid a normal production-style or clinically validated release title. A future maintainer may add a correctly labeled draft/prerelease GitHub Release only with explicit acceptance of that risk, documenting exactly which checks were skipped. Do not upload private research ZIP files or model joblib binaries.
