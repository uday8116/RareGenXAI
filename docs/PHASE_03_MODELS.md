# Phase 03 — Local ML Training, Artifacts and Evaluation

**Research goal:** repeatable candidate disease ranking using local HPO phenotype knowledge and four supervised candidate rerankers. Phase 3 is a *research prototype*, not a clinically validated classifier or a hospital diagnostic system. Model scores are uncalibrated ranking signals, not diagnosis probabilities.

## Scope and status

- Models: TF-IDF candidate retrieval (fits its vocabulary/index), Logistic Regression, Random Forest, XGBoost and MLP.
- Main data: Phase 2 SQLite schema v2, aspect `P` positive disease–phenotype annotations. The model uses only this clinical phenotype feature universe; negative `NOT` annotation knowledge remains available separately.
- Training: synthetic queries sampled from known HPO disease profiles. Split by disease ID before training, hold out full disease IDs for synthetic evaluation; retrieval may see the held-out disease profiles as required by the candidate universe, but the rerankers do not receive their query labels during fitting.
- Important: **not real patient training**; synthetic held-out disease tests are not the same as independent clinical cases.
- GNN remains optional, experimental: it requires PyTorch; its existing validation does not establish superiority to the simpler HPO overlap baseline.
- DeepRare comparison still requires authentic matched-case outputs; never claim a win using unrelated aggregate results.

## Train on Apple M5 (16 GB unified memory)

From the repository root, after phases 1 and 2:

```bash
git switch main && git pull --ff-only origin main
source .venv/bin/activate

python -m src.data
python -m src.knowledge_db build --replace
python -m src.knowledge_db verify --raw-dir data/raw

# CPU-friendly, sequential fitting; no CUDA/Metal setup required.
python -m src.train_ml --seed 42 --train-diseases 600 --test-diseases 120 --queries-per-disease 2 --candidates 40

python -m src.verify_models --raw-dir data/raw
python -m pytest -q tests/test_ml.py tests/test_model_bundle.py
```

Use `--train-diseases 120 --test-diseases 30 --queries-per-disease 1 --candidates 25` for a faster smoke test. Training reruns *overwrite* the previous model bundle at the selected `--output` path; make a backup if you want to preserve it. Keep your free SSD space sufficient and train one CPU-heavy job at a time.

## Training outputs

| Path | Contents |
| --- | --- |
| `models/raregen_ml.joblib` | Saved TF-IDF index plus fitted LR/RF/XGBoost/MLP; trusted pickle format |
| `models/raregen_ml.manifest.json` | Artifact SHA-256, HPO profile fingerprint, source hashes, model names, seed, split, package versions, prediction smoke test |
| `results/ml_trials.csv` | One record per held-out disease, synthetic missingness setting and method |
| `results/ml_summary.csv` | Synthetic Top-1, Top-5, MRR and candidate recall for each model and missingness |
| `results/ml_metadata.json` | Source, training configuration, disjoint disease split IDs and evaluation scope |

`models/` and generated CSVs are Git-ignored. The Phase 3 workflow uploads a complete trusted research model bundle and metadata as a **temporary downloadable GitHub Actions artifact** (retained 14 days), rather than committing binary weights to source control.

## How to verify loading and scores

```bash
python -m src.verify_models --raw-dir data/raw
```

This checks the model SHA-256, verifies the local database has the **same phenotype profile fingerprint and source HPO annotation hashes** as training, reloads all four estimators, compares deterministic rankings, verifies disjoint disease IDs and checks summary/trial table structure.

For programmatic use:

```python
from src.model_bundle import load_verified_bundle

model, manifest = load_verified_bundle("models/raregen_ml.joblib")
ranked = model.rank([("HP:0001250", "confirmed_present")], model="xgboost", top_k=5)
print(ranked)
```

**Security warning:** `joblib` uses Python pickle and can execute code at load time. Only load artifacts created locally or retrieved from a trusted project workflow. SHA checks only detect accidental corruption or mismatch; a malicious actor able to replace both model and manifest could also rewrite the checksum.

## Interpretation and evaluation

- Split type: whole disease IDs held out for synthetic validation, while their feature profiles remain in the full disease candidate index. This is not an unseen medical knowledge base.
- `candidate_recall`: fraction of synthetic queries whose correct disease was retrieved, before reranking. The rerankers cannot recover a disease outside that candidate set.
- `top1`, `top5`, `mrr`: synthetic held-out query ranking metrics; they must not be called independent patient-level diagnostic accuracy.
- Model output is relative score, not a calibrated probability or likelihood of disease.
- Repeat runs with the same seed and exact HPO source release should be reproducible within a matching dependency/runtime environment.
- For *external case* comparison, run the existing RareBench workflow after training; it needs real independently sourced case files and must report disease-ID coverage and matching constraints.

## Acceptance criteria

1. Official HPO source files and Phase 2 DB integrity verified.
2. TF-IDF index and all four fitted estimators saved locally.
3. Model artifact and manifest have matching hashes, features, environment/version provenance, and HPO source fingerprint.
4. Reloaded model reproduces deterministic ranking on a saved fixture.
5. Synthetic held-out disease evaluation has all five methods and all missingness levels, with disjoint train/test disease IDs and candidate recall.
6. Automated unit tests and official source training workflow pass.
7. Owner runs installation and trusted bundle verification on actual M5 Mac.

The GitHub CI build is evidence for code correctness on its runner; it does not prove local Mac setup is complete or that medical performance is clinically validated.
