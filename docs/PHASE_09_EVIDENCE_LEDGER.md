# Phase 9 — Evidence and result-snapshot ledger

This ledger prevents mixing metrics from different RareGenXAI experiments.
**Research only: no clinical performance or diagnostic claim.**

## A. What has been measured

| Evidence snapshot | Source | Method coverage | Meaning | Status |
| --- | --- | --- | --- | --- |
| Historical earlier report | `docs/FINAL_PROJECT_REPORT.md`; run `43485509434` | Four reported methods (overlap, RF, TF-IDF, logistic) | Previously successful retrospective 178-case workflow | Older report. Do **not** merge its model scores with another snapshot |
| Saved six-method archive | `docs/PHASE_07_HISTORICAL_REANALYSIS.md`; run `44467435510` | overlap, XGBoost, logistic, RF, MLP, TF-IDF | Audited archived 178-case prediction rows, not a fresh rerun | **Chosen Phase 9 presentation snapshot** |
| Frozen Phase 7 protocol | `docs/PHASE_07_RESEARCH_EXPERIMENTS.md` | Specified in preregistration | Intended fresh raw-case inference and full audit | **Not verified as completed** |
| Phase 8 real-system acceptance | `docs/PHASE_08_FINAL_AUDIT.md` | Service, browser, model and restart checks | Requires real official HPO/model on owner's Mac | **Not verified as completed** |

The two earlier GitHub Actions runs refer to different model/data snapshots.
For example, older `docs/FINAL_PROJECT_REPORT.md` reports Logistic
Regression Top-1 **27.53%** and TF-IDF Top-1 **30.34%**, whereas the later
audited archive reports Logistic Regression **34.27%** and TF-IDF **29.78%**.
**This is not an arithmetic contradiction; these are different saved runs.
Do not silently combine their per-method results or claim an improvement
between them without a controlled matched experiment.**

## B. Phase 9's selected 178-case archived snapshot

Source: `docs/PHASE_07_HISTORICAL_REANALYSIS.md`,
[original archived run 44467435510](https://github.com/uday8116/RareGenXAI/actions/runs/44467435510).
The archive contains 178 cases, with LIRICAL n=143, MME n=11 and HMS n=24;
six methods yield 1,068 saved case-method ranking outputs.

| Method | Top-1 | Top-5 | MRR |
| --- | ---: | ---: | ---: |
| overlap | 37.64% | 54.49% | 0.453 |
| XGBoost | 36.52% | 51.69% | 0.436 |
| logistic | 34.27% | 48.88% | 0.410 |
| random forest | 32.58% | 42.13% | 0.371 |
| MLP | 30.90% | 41.57% | 0.363 |
| TF-IDF | 29.78% | 43.26% | 0.361 |

**Important limits:** Only archived predictions and their manifests were
available for this independent reanalysis. The original case-phenotype CSV
and full model weights were not in the archive. The CSV SHA and model source
cannot be independently confirmed from that archive. Confidence intervals
are exploratory within-cohort case bootstraps. Equal method names do not
guarantee the same trained model or retrieval universe across runs. No
verified matched-case DeepRare predictions exist.

## C. How to update slides and thesis after a new run

1. Record the successful complete CI/local run URL, workflow attempt, commit SHA,
   model and dataset SHA-256 manifests, cohort counts and methods.
2. Confirm a complete case x method matrix and independent audit, including
   rank/metric consistency and disease coverage.
3. Replace result tables in **all** Phase 9 sources at once:
   `PHASE_09_DISSERTATION_DRAFT.md`,
   `PHASE_09_PRESENTATION.md`,
   `PHASE_09_SPEECH_AND_VIVA.md`, and the standalone PowerPoint.
4. Keep the historical numbers as a **separate** reference, not a baseline
   claiming controlled improvement or clinical generalization.
5. Run `python -m pytest -q tests/test_phase9_docs.py` and recheck
   screenshots and citations before academic submission.

## D. Acceptance ledger

- Phase 9 written technical content: delivered in PR #13.
- GitHub Actions execution on the latest Phase 9 commits: **not verified passing**.
- Physical Mac and real UI screenshot: **not supplied/verified**.
- University dissertation template, title/approval details and signed forms:
  **not supplied/verified**.
- Supervisor approval and final plagiarism/citation review: **not supplied**.

Neither a PR commit nor a static documentation check is a substitute for
the unavailable academic or hardware acceptance evidence.
