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
.venv/bin/python -m src.knowledge_db verify --raw-dir data/raw
.venv/bin/python -m src.knowledge_db search-hpo "seizure"
.venv/bin/python -m src.knowledge_db search-disease "Marfan"
```

Run `.venv/bin/python -m src.knowledge_db build --replace` to deliberately replace an existing local database after validation, especially when upgrading from schema v1 to schema v2. Back up the old local file first. The default database is `data/local/raregen.sqlite3` (ignored by Git). See [Phase 2 database and search documentation](docs/PHASE_02_DATA_DATABASE.md).

## Phase 3: trained ML models and reproducible verification

The Phase 3 workflow fits TF-IDF retrieval and four supervised rerankers (Logistic Regression, Random Forest, XGBoost, MLP) on **synthetic phenotype queries from the official Phase 2 SQLite database**. This is disease-disjoint synthetic validation, not patient-level or clinical diagnosis accuracy.

```bash
# Requires Phase 2 database built (schema v2)
.venv/bin/python -m src.train_ml --seed 42 --train-diseases 600 --test-diseases 120 --queries-per-disease 2 --candidates 40
.venv/bin/python -m src.verify_models --raw-dir data/raw
```

The saved model lives at `models/raregen_ml.joblib` with a matching `models/raregen_ml.manifest.json`. The manifest verifies file integrity and input dataset provenance, and a fresh load must reproduce stored predictions. All binary models stay out of Git and are available in the Phase 3 GitHub workflow as a short-lived artifact. See [Phase 3 model training guide](docs/PHASE_03_MODELS.md), [historical Phase 3 metrics](docs/PHASE_03_REVIEW.md), and [Phase 3 independent correctness review](docs/PHASE_03_FINAL_AUDIT.md).

**Important:** Only load trusted local or trusted project CI joblib files. ML ranking scores are not calibrated probabilities.


## Phase 4: locally running FastAPI backend

The versioned read-only HTTP API connects Phase 2 SQLite, Phase 3 trusted models and the next-phase frontend. It is **not** a hosted website or a clinical diagnostic system.

~~~bash
source .venv/bin/activate
python -m pip install -r requirements.txt
# Requires local HPO SQLite knowledge and, for ML endpoints, a trained verified model.
bash scripts/start_api.sh
~~~

Open **http://127.0.0.1:8000/docs** for interactive Swagger/OpenAPI documentation, **http://127.0.0.1:8000/redoc** for the reference, or **http://127.0.0.1:8000/api/v1/health** for liveness. Versioned APIs include phenotype and disease search, knowledge statistics, model readiness, and explainable research ranking.

The server binds to loopback only and never stores patient observations. No AWS, Railway or external database is needed. See [Phase 4 backend plan and API documentation](docs/PHASE_04_BACKEND.md). The professional website and model dashboard remain a separate frontend phase.

## Phase 5: professional React research website (local-only)

Phase 5 adds a responsive React + Vite website connected to the FastAPI research backend. It includes the overview dashboard, HPO phenotype-input workbench, explainable candidate rankings, disease explorer, historical model-comparison chart and API documentation. The research score is **never** a calibrated disease probability.

```bash
# Terminal 1 — from repository root, once Phase 2 data and Phase 3 models are prepared
bash scripts/start_api.sh

# Terminal 2 — from repository root
cd frontend
npm install
npm run test
npm run dev
```

Open **http://127.0.0.1:5173**. The frontend only calls the same-origin `/api/v1` endpoint through Vite's local proxy to `127.0.0.1:8000`. An unavailable backend is shown honestly: the workbench does not produce fake predictions.

The model dashboard links to historical 178-case RareBench measurements (it is **not** an automatic live evaluation). No external cloud hosting, patient identifiers, localStorage or GPU is required. The UI runs locally on the Apple M5 with 16 GB RAM. See [Phase 5 implementation and Mac guide](docs/PHASE_05_FRONTEND.md).

Phase 4 security review was integrated into the Phase 10 code before merging. Do not consider the new frontend fully accepted until its GitHub CI and manual local integration pass.

### Phase 5 research export and local acceptance

After running an analysis, you can deliberately **export the displayed disease rankings** as CSV or JSON to your own Mac. CSV text is protected against spreadsheet formula injection. Files may contain matched phenotype IDs, so take care before sharing. Ordinary HPO observations stay in memory unless you choose an export. The website never invents predictions when offline.

The [Phase 5 independent acceptance audit](docs/PHASE_05_FINAL_AUDIT.md) records the stale-response fix, keyboard HPO improvements, opt-in export, smoke test and required verification. From the repository root, after starting both the API and React server, run:

```bash
python scripts/smoke_phase5.py
```

The Phase 5 PR remains unmerged until actual Node/Vitest and Vite build checks execute. The pre-execution GitHub Actions failures are not proof of test success.

## Phase 6 — Explainability and same-case model comparison

Phase 6 adds an auditable **Explainability Laboratory** inside the React Phenotype Workbench. Select a candidate disease to inspect exact and ontology-related HPO evidence, signed supporting/contradicting contributions for overlap/semantic baselines, and reproducible shared-ancestor links. Compare 2–4 locally available ranking methods using identical phenotype inputs, or run a one-phenotype-removed sensitivity check. These are **research ranking interpretations, not medical diagnosis or SHAP**.

The local FastAPI service provides `POST /api/v1/explain` in addition to `POST /api/v1/rank`. All requests are read-only and processed on the same Mac. The new explanation endpoint never invents feature attributions for XGBoost, MLP, Random Forest or other trained methods.

```bash
source .venv/bin/activate
python -m pytest -q tests/test_explainability.py tests/test_api.py
cd frontend
npm run test:logic
npm run test
npm run build
```

With both local servers running, open **http://127.0.0.1:5173/workbench** and run a ranking to reveal the Phase 6 panels.

Full methodology, verification evidence, limitations and M5 commands are in [Phase 6 explanation and comparison guide](docs/PHASE_06_EXPLAINABILITY.md). Phase 6 is stacked on the still-open Phase 5 implementation branch. Neither phase should be treated as merged or fully verified before GitHub CI and the physical Mac checks pass.

### Phase 6 independent review and strict verification

Phase 6 now rejects nonclinical HPO categories, checks both model and HPO source fingerprints across real API calls, and hides inconsistent explanations. It includes a full official-data/model acceptance test. Run:

```bash
bash scripts/verify_phase6.sh --quick
cd frontend && npm install && cd ..
bash scripts/verify_phase6.sh --full
```

The quick mode is **not final acceptance**. Full mode requires the verified HPO SQLite database, trained model bundle, React tests and built Vite website. See the [Phase 6 final audit](docs/PHASE_06_FINAL_AUDIT.md). GitHub Actions currently fails before running any steps, so PR #10 remains unmerged.


## Phase 7 — Preregistered RareBench research experiments

The new [Phase 7 protocol and results guide](docs/PHASE_07_RESEARCH_EXPERIMENTS.md) implements strict external-case model evaluation, independent metric rechecking, per-cohort 95% **exploratory** bootstrap intervals, paired comparison with the overlap baseline, error analysis, and source/model SHA-256 provenance.

**Quick tests — no patient data needed:**

```bash
source .venv/bin/activate
bash scripts/verify_phase7.sh --quick
```

**Full official-data experiment** (requires real, licensed/de-identified RareBench cases and verified Phase 2/3 artifacts):

```bash
python -m src.rarebench --limit-per-subset 100000
bash scripts/verify_phase7.sh --full
```

The full command freezes the exact case set, model and methods *before* generating new ranking outputs; it fails on missing artifacts, incomplete case/method coverage or incorrect metrics. It will not overwrite an existing frozen evaluation plan. Its generated patient-case results are ignored by Git and must be inspected before reporting.

**Academic restrictions:** this is retrospective published-case evaluation with possible HPO literature overlap. It is not prospective clinical validation, not a matched DeepRare comparison, and ranking scores are not calibrated diagnostic probabilities. Previously published RareBench numbers are historical snapshots, not new Phase 7 results. The Phase 7 PR remains dependent on the still-unmerged Phase 6 implementation.

### Phase 7 independent audit and historical evidence

The Phase 7 correctness review now rejects logically impossible ranks, binds the actual inference process to the frozen case/model/method plan **before** predictions, and optionally reloads the trusted verified model to cross-check disease-ID coverage. A full successful run also produces `results/phase7_research_report.md` from audited cohort metrics.

**Historical evidence was independently reanalysed:** the successful published-case benchmark archive from [GitHub Actions run 44467435510](https://github.com/uday8116/RareGenXAI/actions/runs/44467435510) contains 178 cases and 1,068 saved rankings. Every case/method row was checked against the historical reported metrics; exploratory paired confidence intervals and error breakdowns were recomputed from those archived predictions. Exact-overlap Top-1 was **37.64%** on that old snapshot. This is **not** a newly executed Phase 7 benchmark and not clinical validation, and the archive does not contain the original HPO observations or the trained model bytes.

See [archived RareBench reanalysis](docs/PHASE_07_HISTORICAL_REANALYSIS.md) and the reusable `src/phase7_historical_reaudit.py` CLI. Its synthetic archive regression suite passed **10/10 tests** locally using byte-identical committed code. The expanded current live-evaluation audit tests and a new full official HPO+RareBench run still require CI or the owner's Mac. Phase 7 PR #11 therefore remains open.


## Phase 8 — Automated system verification (local Mac)

Phase 8 implements an offline guard suite and a strict real-system check that
starts FastAPI and the React Vite server, exercises the actual loopback API through
the frontend proxy (HPO search, all installed ML ranking methods, explanations and
invalid-input rejection), then shuts both servers down and repeats a cold start.

```bash
bash scripts/verify_phase8.sh --quick  # offline tests, not acceptance
bash scripts/verify_phase8.sh --full   # real HPO/model data, React tests/build, two restarts
```

The full command requires verified official HPO data, a trained verified model
and local Node dependencies. Stop other services on ports 8000/5173 first.
See [Phase 8 system verification and outstanding acceptance](docs/PHASE_08_SYSTEM_VERIFICATION.md).
Phase 8 does not become accepted merely because the scripts were committed:
GitHub CI and local Mac checks must actually pass. Phase 7 acceptance remains separate.


## Phase 9 — Dissertation, user documentation and viva preparation

Phase 9 contains the research user guide, API and SQLite v2 schema reference,
technical dissertation draft, editable 12-slide outline, presentation speech,
25 viva questions and documentation consistency tests:

- [Phase 9 plan and acceptance](docs/PHASE_09_PLAN_AND_ACCEPTANCE.md)
- [Local user guide](docs/PHASE_09_USER_GUIDE.md)
- [API and schema reference](docs/PHASE_09_API_AND_SCHEMA.md)
- [M.Tech dissertation working draft](docs/PHASE_09_DISSERTATION_DRAFT.md)
- [Presentation slide source](docs/PHASE_09_PRESENTATION.md)
- [Speech and viva questions](docs/PHASE_09_SPEECH_AND_VIVA.md)
- [Evidence ledger: separate archived benchmark snapshots](docs/PHASE_09_EVIDENCE_LEDGER.md)
- [Independent Phase 9 final audit and remaining acceptance](docs/PHASE_09_FINAL_AUDIT.md)

```bash
python -m pytest -q tests/test_phase9_docs.py
```

The historical archived 178-case findings are **not** a successful fresh Phase 7
evaluation. University formatting, real screenshots, examiner/supervisor approval,
and the still-pending Phase 7/8 acceptance are separate requirements.


## Phase 10 — Local release and handover

Phase 10 prepares a **research-only** release candidate with source-aware
handover instructions, an explicit acceptance matrix, and a local artifact
backup/restore tool with per-file SHA-256 integrity checks. The proposed
`v0.10.0-rc1` tag has **not been created**; upstream PRs, GitHub CI,
full Phase 7/8 validation, and supervisor approval remain outstanding.

```bash
bash scripts/verify_phase10.sh --quick  # synthetic backup security + docs checks
bash scripts/verify_phase10.sh --full   # real model/data + app + backup/restore
```

For a private, local research backup:

```bash
python scripts/phase10_backup.py create --out ~/RareGenXAI-research-backup.zip
python scripts/phase10_backup.py verify --archive ~/RareGenXAI-research-backup.zip
python scripts/phase10_backup.py restore --archive ~/RareGenXAI-research-backup.zip \
  --destination ~/RareGenXAI-restore-test
```

Do not publish local research backups or load untrusted model joblib files.

- [Phase 10 release and handover](docs/PHASE_10_RELEASE_HANDOVER.md)
- [Phase 10 acceptance matrix](docs/PHASE_10_ACCEPTANCE.md)
- [Draft release notes: not released](docs/PHASE_10_RELEASE_NOTES.md)
- [Independent Phase 10 audit and remaining blockers](docs/PHASE_10_FINAL_AUDIT.md)

See [Phase 4 independent local API security review](docs/PHASE_04_REVIEW.md) for preserved loopback controls and source integrity checks.
