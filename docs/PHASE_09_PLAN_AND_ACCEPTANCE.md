# Phase 9 — Documentation, dissertation and viva readiness

**Roadmap goal:** User guide, API docs, schema, thesis draft, slides, speech and viva Q&A; all documents must agree with actual code and *verified* results.

## Implemented deliverables

| Deliverable | File | Acceptance scope |
|---|---|---|
| Installation, interactive use, local demo and troubleshooting | `PHASE_09_USER_GUIDE.md` | Text and paths grounded in Phase 4–8 scripts |
| API, data flow, response/validation and database table dictionary | `PHASE_09_API_AND_SCHEMA.md` | Cross-check routes with `src/api.py`, tables with `src/db_schema.py` |
| Dissertation working draft | `PHASE_09_DISSERTATION_DRAFT.md` | Technical draft only; no forged clinical or newer evaluation |
| 12-slide editable presentation source | `PHASE_09_PRESENTATION.md` | Presenter must transfer to university PowerPoint template |
| Plain-English demo speech, 25 viva answers | `PHASE_09_SPEECH_AND_VIVA.md` | Must use actual observed state at defense |
| Completion/evidence boundaries | This file | Keeps technical preparation separate from official approval |

## Evidence ledger

- Historical measured metrics only: `docs/PHASE_07_HISTORICAL_REANALYSIS.md` and GitHub Actions archived results [run 44467435510](https://github.com/uday8116/RareGenXAI/actions/runs/44467435510), 178 eligible saved RareBench cases; six methods. The archived source case observations and model weights cannot be recovered from that ZIP.
- Recent Phase 7 official end-to-end rerun: **not verified passing**.
- Recent Phase 8 automated and real Mac restart acceptance: **not verified passing**.
- Same-case authentic DeepRare predictions: **unavailable**.
- Public hosted website, clinical validation, campus approval: **not verified**.

## Pre-submission gates

- [x] User guide and architecture/API/schema reference written.
- [x] Dissertation technical draft written, with historical-results labeling.
- [x] 12-slide editable Markdown presentation source and full speech/viva prep written.
- [ ] Latest documentation integrity automation executes successfully.
- [ ] Real application screenshots and live or recorded local demonstration captured.
- [ ] University template formatting, approved title/certificates/declarations inserted.
- [ ] Supervisor reviews claims, novelty, citations and ethics statements.
- [ ] Latest Phase 7/8 acceptance completed and any new data/results reflected.
- [ ] Phase 9 PR merged after predecessor dependencies are resolved.

## Safe update rule

When newer verified results become available, update *all* result tables in the dissertation, presentation and speech together and cite the exact run/artifact, input/model hashes, case count and methods. Do not silently mix older and newer snapshots. This is an academic deliverable, not a clinical device submission.

## Optional documentation verification

`python -m pytest -q tests/test_phase9_docs.py` checks file presence, declared endpoints/table names, matched archived result numbers and honesty/limitations. It is a static consistency check, **not** a proof that medical results or system acceptance are correct.
