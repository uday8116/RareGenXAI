# RareGenXAI

**Explainable AI-Based Classification of Rare Genetic Disorders Using Clinical Phenotypes and Human Phenotype Ontology**

A reproducible **research prototype** that prioritizes candidate rare diseases using official HPO disease–phenotype annotations. It provides transparent per-finding score contributions and an experimental evidence-quality weighting scheme.

> **Safety:** This is not a medical device and must not be used for diagnosis, treatment, or clinical decision-making. Scores are ranking scores, **not** probabilities. The application uses disease annotation knowledge; an external retrospective patient-case evaluation has also been completed.

## Features
- Download and parse official HPO ontology (`hp.obo`) and disease annotations (`phenotype.hpoa`)
- Exact phenotype overlap and ontology-aware similarity baselines
- Proposed evidence-quality scoring: confirmed present (1.0), suspected present (0.4), confirmed absent (-0.6), unknown (0.0)
- Per-phenotype score decomposition for every candidate
- Top-five interactive Streamlit interface
- Controlled synthetic benchmark with Top-1, Top-5, and mean reciprocal rank (MRR)
- Unit tests

## Phase 1: local Apple Silicon setup (M5, 16 GB)

The first phase provides a repeatable local setup and diagnostic toolchain. It **does not** yet install the planned React/FastAPI application or provide newly trained models.

On macOS, install native Python 3.11 (recommended), Git, Homebrew OpenMP (`libomp`) for XGBoost, and optionally Node.js (needed for the later React phase). With Homebrew: `brew install python@3.11 git node libomp` (the bootstrap can also install missing `libomp` automatically). Then:

```bash
git clone https://github.com/uday8116/RareGenXAI.git
cd RareGenXAI
bash scripts/bootstrap_macos.sh
bash scripts/verify_local.sh
```

To also prepare official HPO data, run `bash scripts/bootstrap_macos.sh --data`, then `bash scripts/verify_local.sh --full`. This downloads public research data and requires internet access. Start the **existing** Streamlit prototype with `.venv/bin/python -m streamlit run app.py`.

- [Detailed macOS guide](docs/LOCAL_DEVELOPMENT_MACOS.md)
- [Phase 1 audit and acceptance criteria](docs/PHASE_01_FOUNDATION.md)
- [Seven-day phased implementation plan](docs/PROJECT_IMPLEMENTATION_ROADMAP.md)

## Manual installation (macOS Apple Silicon)
Install Python 3.11 or 3.12, then in Terminal:

```bash
git clone https://github.com/uday8116/RareGenXAI.git
cd RareGenXAI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m src.data
python -m pytest -q
streamlit run app.py
```

Open the local Streamlit URL displayed in Terminal (usually http://localhost:8501).

## Reproducible synthetic benchmark
```bash
python -m src.evaluate --trials 100 --seed 42
```
Results are written to `results/synthetic_trials.csv` and `results/synthetic_summary.csv`. No accuracy numbers are claimed until the experiment is actually run. Synthetic queries are sampled from the same disease annotation resource used for matching, so they are **not** independent clinical validation. The evaluation is intended for debugging and robustness exploration only.

## Method
The HPO ontology provides parent relationships. We compute disease-frequency information content (IC) for HPO terms and ancestors. Semantic similarity between two HPO terms uses the most informative common ancestor (MICA), normalized by the larger term IC. Each observed phenotype is compared with the closest phenotype in each disease profile. Weighted contributions are summed and divided by total absolute evidence weight. Confirmed absent evidence is penalized when its phenotype matches a candidate profile. Unknown features contribute zero.

**Important limitations:** The proposed weights are illustrative design choices, not learned or clinically validated. The current annotation-based negative penalty is a simplified heuristic, not a calibrated probability model. Suspected evidence is simulated for benchmarking; HPO annotations do not contain patient-specific confirmation status. Existing methods (including LIRICAL) already support negative phenotype evidence. This repository does not establish novelty or clinical accuracy. Stronger research requires independent cases, literature comparison, and a sensitivity analysis of the weights.

## Project structure
- `src/data.py`: HPO download, parse and profile construction
- `src/ranking.py`: baseline and evidence-aware ranking
- `src/evaluate.py`: controlled synthetic evaluation
- `app.py`: Streamlit web app
- `tests/`: automated tests
- `docs/`: methodology and research limitations

## Data provenance
The source files are fetched at runtime from the official HPO PURLs, and a SHA-256 manifest is written to `data/raw/manifest.json`. The source files and processed profiles are excluded from Git to avoid committing third-party datasets. Consult the HPO project's licensing and attribution requirements: https://hpo.jax.org/ and https://github.com/obophenotype/human-phenotype-ontology.

## Research references
- Köhler et al., 2009, Phenomizer: https://doi.org/10.1016/j.ajhg.2009.09.003
- Robinson et al., 2020, LIRICAL: https://doi.org/10.1016/j.ajhg.2020.06.021
- HPO 2024: https://pmc.ncbi.nlm.nih.gov/articles/PMC10767975/

## Verified external RareBench evaluation

A GitHub Actions run successfully evaluated **178 eligible externally sourced patient cases** (LIRICAL 143, MME 11, HMS 24). Overall Top-1 / Top-5 results: exact overlap **37.64% / 54.49%**, Random Forest **32.58% / 40.45%**, TF-IDF **30.34% / 43.26%**, and Logistic Regression **27.53% / 46.07%**. Exact overlap performed best overall. This is a retrospective benchmark, **not clinical validation**, and no identical-case DeepRare predictions were available.

- [Verified run and downloadable results](https://github.com/uday8116/RareGenXAI/actions/runs/43485509434)
- [Final technical report](docs/FINAL_PROJECT_REPORT.md)
- [Full cohort metrics](docs/VERIFIED_EXTERNAL_RESULTS.md)
- [DeepRare comparison limitations](docs/DEEPRARE_MATCHED_COMPARISON.md)
- [Web deployment guide](docs/WEB_DEPLOYMENT.md)

## Next research steps
1. Validate the HPO annotation schema and freeze a release.
2. Test on independent, ethically obtained clinical cases.
3. Compare against a published phenotype-ranking tool on matched inputs.
4. Tune and test evidence-quality weights without leakage.
5. Quantify uncertainty and explanation faithfulness before any clinical claims.

## Phase 2: local HPO knowledge database

Phase 2 provides a versioned, reproducible SQLite knowledge base using official HPO data. It stores **only disease/phenotype knowledge**, not identifiable patient records or diagnoses.

```bash
.venv/bin/python -m src.data
.venv/bin/python -m src.knowledge_db build
.venv/bin/python -m src.knowledge_db verify
.venv/bin/python -m src.knowledge_db search-hpo "seizure"
.venv/bin/python -m src.knowledge_db search-disease "Marfan"
```

Run `.venv/bin/python -m src.knowledge_db build --replace` to deliberately replace an existing local database after validation. The default database is `data/local/raregen.sqlite3` (ignored by Git). See [Phase 2 database and search documentation](docs/PHASE_02_DATA_DATABASE.md).
