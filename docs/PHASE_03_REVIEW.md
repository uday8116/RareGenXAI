# Phase 03 — Audit, verified model training and research results

> **Historical implementation report for PR #5.** Its accuracy and candidate-recall figures were measured before the [independent Phase 3 retrieval/evaluation audit](PHASE_03_FINAL_AUDIT.md). Do not use these numbers for the revised model without a new benchmark.

**Review date:** 2026-11-19. **Reference machine:** Apple M5, 16 GB unified memory. **Research status:** runnable training pipeline tested in GitHub CI; physical M5 run not yet confirmed. **Scope:** candidate disease ranking, not clinical diagnosis.

## 1. Audit of original implementation

| Requirement | Original gap | Implemented resolution |
| --- | --- | --- |
| Structured data source | Training read legacy JSON profiles, which could include non-phenotypic annotation aspects | Train from Phase 2 schema-v2 SQLite, aspect `P` only by default |
| Model provenance | Single `joblib` file with no explicit source fingerprint | Manifest with SHA-256, source URLs/hashes, profile fingerprint, seed, feature schema, package versions |
| Split reproducibility | Hold-out counts reported but exact disease IDs not preserved | Lists of train and held-out disease IDs, with explicit disjointness validation |
| Loading and trust | Saved file used `joblib.load` with no file hash/fit check | Trusted-local manifest check, exact smoke ranking verification and mismatch rejection |
| Evidence packaging | Model files ignored by Git but not exported as trained CI artifact | GitHub Actions artifact with model, manifest, synthetic trial/summary/metadata CSV/JSON, HPO source manifest |
| External comparison | Old report could use legacy all-aspect profiles and different training config | Both overlap baseline and ML now use one candidate universe; evaluation trains 600/120 config |
| Data download resilience | Transient HPO server disconnect could fail pipeline or leave a partial raw file | Retry, temporary file and atomic replace; offline mocked tests |
| Tests | No full model-persistence corruption or profile mismatch test | Dedicated regression tests, official training smoke, Linux + Apple Silicon runners |

## 2. Models that are really fitted

| Component | Status | Role |
| --- | --- | --- |
| TF-IDF | Fitted vectorizer/index | Initial disease retrieval |
| Logistic Regression | Trained estimator | Candidate reranking |
| Random Forest | Trained estimator | Candidate reranking |
| XGBoost | Trained estimator | Candidate reranking |
| MLP | Trained estimator | Candidate reranking |
| Exact HPO overlap | Non-trainable baseline | Comparison |
| GNN | Optional separate experiment | Not in core saved Phase 3 bundle |

All supervised models use **synthetic phenotype queries created from disease annotation knowledge**. No clinical patient records were used for training. The models are not certified or calibrated diagnostic systems.

## 3. Verified training job

GitHub run: https://github.com/uday8116/RareGenXAI/actions/runs/44467025308

- HPO phenotype-only candidate universe in the saved model: **12,867 diseases**.
- Synthetic training disease IDs: **600**.
- Synthetic held-out disease IDs: **120**, disjoint from training.
- Training queries per selected disease: **2**.
- Retrieval candidates: **40**.
- Synthetic evaluation rows: **2,400** (120 held-out diseases × 4 missingness settings × 5 methods).
- All four trained estimators plus TF-IDF index persisted, hash-verified and reloaded successfully.
- Workflow runs synthetic model bundle tests on Ubuntu and Apple Silicon. The full-size official-data training job runs on Ubuntu; it does not configure the user's physical M5.

**Artifacts:** The workflow uploads `phase3-synthetic-hpo-trained-model-ubuntu`, containing the model weights, manifest, raw-HPO provenance manifest, synthetic evaluation records, model summary and metadata. The artifact is temporary; download it before retention expires or retrain locally. Joblib files must only be loaded from trusted sources.

## 4. Synthetic hold-out evaluation

The synthetic test selects symptoms directly from held-out disease annotation profiles. It can therefore appear much easier than identifying a disease from real clinical notes. For example, in the 0%-missingness condition, Top-1 rates were:

| Method | Synthetic Top-1 (0% missing phenotypes) |
| --- | ---: |
| TF-IDF | 96.67% |
| Logistic Regression | 98.33% |
| Random Forest | 96.67% |
| XGBoost | 97.50% |
| MLP | 98.33% |

These are **synthetic hold-out results, NOT independent patient-case diagnostic accuracy**. They must not be compared directly with clinical performance claims.

## 5. Aligned RareBench external-case evaluation

Source: public RareBench `chenxz/RareBench`, 178 eligible single-diagnosis cases across LIRICAL, MME and HMS cohorts.

Verified run with the same **600 train / 120 held-out disease** training configuration: https://github.com/uday8116/RareGenXAI/actions/runs/44467237086

| Method | Cases | Top-1 | Top-5 | MRR |
| --- | ---: | ---: | ---: | ---: |
| Exact HPO overlap | 178 | **37.64%** | **54.49%** | **0.4530** |
| XGBoost | 178 | 36.52% | 51.69% | 0.4362 |
| Logistic Regression | 178 | 34.27% | 48.88% | 0.4099 |
| TF-IDF | 178 | 29.78% | 43.26% | 0.3606 |
| MLP | 178 | 30.90% | 41.57% | 0.3646 |
| Random Forest | 178 | 29.21% | 41.57% | 0.3566 |

Recorded disease-ID coverage: **99.44%**. The ML methods retrieve at most 40 candidates, whereas the overlap baseline ranks the whole disease universe; this difference must be acknowledged when interpreting performance.

**Finding:** Exact phenotype overlap remains the strongest overall Top-1/Top-5 method in this run. More complex models do not demonstrate superiority here.

**Limitations:** RareBench examples are published case-based external observations, not a prospective clinical trial. Source literature and disease annotations can overlap. Matching disease identifiers and checking per-cohort errors remain crucial. No genuine matched-case DeepRare comparison has been performed. Performance is not established for routine clinical diagnosis.

## 6. Completion checklist

- [x] Train and save TF-IDF + Logistic Regression, Random Forest, XGBoost and MLP on official HPO phenotype knowledge
- [x] Source data provenance and deterministic fingerprint in model manifest
- [x] Stored seed, training/held-out disease IDs and package versions
- [x] Reproducible synthetic disease-disjoint evaluation
- [x] Post-load model integrity and prediction verification
- [x] Automated regression, Ubuntu and Apple Silicon model tests
- [x] Real official-data CI training and temporary artifact publication
- [x] External RareBench run with all major methods on matched cases
- [x] Comparison result caveats and documentation
- [ ] **Owner's physical Apple M5 local model training, restart and demonstration**

**Core Phase 3 source implementation is complete when the final PR checks pass.** Actual local Mac verification cannot be claimed from GitHub CI. GNN optimization and a clinical holdout remain research extensions outside the core Phase 3 acceptance criteria.

## 7. Mac handoff and verification

```bash
cd RareGenXAI
git switch main
git pull --ff-only origin main
source .venv/bin/activate

python -m src.data
python -m src.knowledge_db build --replace
python -m src.knowledge_db verify --raw-dir data/raw

python -m src.train_ml --seed 42 --train-diseases 600 --test-diseases 120 --queries-per-disease 2 --candidates 40
python -m src.verify_models --raw-dir data/raw
python -m pytest -q tests/test_ml.py tests/test_model_bundle.py tests/test_data_download.py
python -m streamlit run app.py
```

Back up any existing local DB and model bundle before replacing them. A new HPO download can have different SHA-256 hashes and different case counts, so record the local manifest when reporting reproducibility.

## 8. Phase 4 handoff

Use `src.model_bundle.load_verified_bundle()` for trusted local model inference and `src.db_access.open_readonly()` for HPO search. Expose status and provenance without transmitting or storing identifiable patient information. Keep the research-only warning visible, report model scores as ranking signals rather than calibrated probabilities, and validate all API HPO IDs and observation statuses.

## 9. Reproducibility audit note

During the Phase 3 review, two separate CI jobs (same declared seed, training sizes, source snapshot fingerprint and package versions) produced slightly different Random Forest external results. This is a reproducibility concern worth investigating. The final pipeline therefore records the SHA-256 of the **actual training feature matrix and labels** and applies fixed hash/BLAS/OpenMP thread settings to research CI. Reporting should refer to a specific run and its manifests. Do not treat a cross-run metric as guaranteed invariant until tested repeatedly under a fixed environment.
