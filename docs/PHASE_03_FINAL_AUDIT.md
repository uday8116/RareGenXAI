# Phase 3 independent review: retrieval, data integrity, and release acceptance

**Date:** 2026-11-19. **Target:** local Apple M5, 16 GB unified memory.
**Scope:** core phenotype-based disease prioritization, synthetic supervised rerankers, saved-model verification, and reproducible evaluation. This is research software, **not** a diagnostic system.

## Baseline reviewed

The first Phase 3 release was merged as `7a9360b` (PR #5), with all four GitHub workflows passing. It produced a trusted model artifact from official HPO data and published an external RareBench evaluation on 178 eligible cases. **Those results belong to the older retrieval implementation.** They are not valid measurements of this review's revised model.

### Confirmed review findings

| Finding | Impact | Resolution |
| --- | --- | --- |
| TF-IDF retrieval padded to k with arbitrary zero-similarity diseases | Nonmatching diagnoses could enter Top-k and artificially increase candidate recall | Keep only positive-similarity matches at inference |
| `numpy.argpartition` could select arbitrary ties at the k cutoff | Equal-score candidates could change across executions | Include all boundary ties, then order by score descending / disease ID ascending |
| Training often needs negative examples when queries match only one disease | A strict no-zero retrieval list could leave the classifier with one class | Seeded random negative padding **only during synthetic training**, never during inference or held-out tests |
| Saved synthetic CSV rows were checked only for counts and broad metric bounds | Missing/duplicated patient-method combinations and falsified summaries could pass | Audit every case × missingness × method combination and recompute all reported metrics from raw trial rows |
| Old model bundle could load with changed candidate retrieval logic | Model weights and evaluation evidence no longer matched runtime policy | Manifest schema **v2** checks retrieval and negative sampling policy; old models require retraining |
| Model and JSON manifest were published separately | Interrupted local save could overwrite a previously working bundle | Verify staging pair before publish; back up and restore old pair on failure; concurrent reader must still fail closed during swap |

### Modified system

`HPO v2 SQLite (aspect P) -> TF-IDF candidate retrieval (positive matches only; stable ties) -> trained reranker (LR/RF/XGBoost/MLP) -> model manifest v2 -> case-level synthetic and RareBench evaluation`.

The simulated negative candidates in the training phase are **not patient observations**, diagnoses or evidence for selecting inference candidates. The candidate-recall metric must be evaluated again after this retrieval change.

### Verification gates

- [x] Source code changes and regression tests implemented in review PR
- [ ] Latest Ubuntu and Apple Silicon model unit CI green
- [ ] Latest official HPO training workflow green with saved model v2 and manifest
- [ ] Latest complete repository integration workflow green
- [ ] Updated identical-case RareBench evaluation green; write the exact run ID and numbers here once verified
- [ ] GitHub changes merged into main after checks
- [ ] Physical Apple M5 local installation, training, reload and user interface verified

A green workflow confirms a GitHub runner, **not** that the user's own laptop executed the scripts.

## Run on your M5 after merge

```bash
cd RareGenXAI
git switch main && git pull --ff-only origin main
source .venv/bin/activate

python -m src.data
python -m src.knowledge_db build --replace
python -m src.knowledge_db verify --raw-dir data/raw

# Must retrain: old model manifest schema is incompatible by design.
python -m src.train_ml --seed 42 --train-diseases 600 --test-diseases 120 --queries-per-disease 2 --candidates 40
python -m src.verify_models --raw-dir data/raw

python -m pytest -q tests/test_ml.py tests/test_model_bundle.py tests/test_phase3_integrity.py
python -m streamlit run app.py
```

Back up existing generated model/database artifacts before replacing them. Local model files are joblib/pickle; load only model files trained on your Mac or created by a trusted repository workflow. A hash plus JSON manifest is **not a digital signature**. The two-file publication protocol has best-effort rollback but cannot guarantee a concurrent reader sees both replaced at the exact same instant.

## Research limitations

- No identified patient data is collected. Training uses synthetic HPO-derived examples, not real patients.
- Synthetic held-out disease tests are not independent clinical validation, even when all disease IDs are disjoint.
- Exact-overlap has historically outperformed most trained rerankers on this published RareBench slice. The revised model's figures must be measured before selecting a best method.
- Retrieval errors cannot be fixed by a reranker if the disease is missing from its top-k shortlist. Report candidate recall separately.
- A full trained GNN, clinical validation, matched-case DeepRare comparisons and the React/FastAPI dashboard are **not part of Phase 3 core**; they remain separate scope.
- Source releases are mutable; preserve official HPO file hashes and exact environment versions for dissertation tables.
