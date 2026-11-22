# RareGenXAI — Local user and demonstration guide

**Audience:** M.Tech examiners, researchers and student developers. **Not for diagnosis, treatment, medical decisions or real patient intake.**

## Before you begin

The research UI uses a local FastAPI process, React/Vite and official Human Phenotype Ontology (HPO) knowledge stored in a schema-v2 SQLite file. Trained rerankers require a locally trusted, verified joblib model and its matching manifest. Use Python 3.11, Node.js 22, npm and the repository dependency files; follow `docs/LOCAL_DEVELOPMENT_MACOS.md`. Never download and deserialize an untrusted model.

```bash
git switch phase-09/documentation-viva
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# On first setup only, download official source and prepare local knowledge:
python -m src.data
python -m src.knowledge_db build
python -m src.knowledge_db verify --raw-dir data/raw
# Train only if no verified compatible local bundle exists:
python -m src.train_ml --seed 42 --train-diseases 600 --test-diseases 120 --queries-per-disease 2 --candidates 40
python -m src.verify_models --db data/local/raregen.sqlite3 --raw-dir data/raw
cd frontend && npm install && cd ..
```

If a database already exists, follow its backup and version-migration instructions before rebuilding. The repository excludes downloaded data and model bytes. Internet access is needed for initial public source downloads and package installation.

## Start and stop

Terminal A: `bash scripts/start_api.sh`, then open `http://127.0.0.1:8000/docs`.
Terminal B: `bash scripts/start_frontend.sh`, then open `http://127.0.0.1:5173`. Both must run on the same machine. Stop each with Ctrl+C. No public hosting is part of this phase.

## Demonstrate the research workflow

1. Check API readiness at `/api/v1/ready` and model availability at `/api/v1/models`. `/health` alone does **not** establish a ready dataset.
2. Open the React phenotype workbench. Search for a *public example* phenotype such as seizure (`HP:0001250`); add one or more canonical clinical HPO IDs.
3. Mark each observation as confirmed present, suspected present, confirmed absent or unknown. At least one must be present or suspected. Do not enter identifying patient notes.
4. Run `overlap` or `semantic`; if a verified trained bundle is available, select TF-IDF, Logistic Regression, Random Forest, XGBoost or MLP. Inspect the candidate names, order, source fingerprints and evidence.
5. Select a candidate to open the explanation panel. For baseline ranking this shows ontology-related and exact evidence; for learned rerankers displayed feature values are **not** causal explanations or SHAP attributions.
6. Compare methods using the same entered HPO terms. The historical dashboard is not a new experiment.
7. If exporting a report, check it before sharing: exported data can contain HPO observations. Do not store identifiable clinical records.

## Error handling

| Symptom | Meaning / next check |
|---|---|
| API `/health` works but `/ready` returns 503 | Official SQLite database missing or invalid; verify HPO import |
| Model unavailable/incompatible | Verify trusted `models/raregen_ml.joblib`, manifest and HPO provenance |
| 422 for an observation | Invalid/obsolete/nonclinical HPO ID, repeated alias, unsupported status, empty positive set or input limit |
| Frontend unreachable | Check `bash scripts/start_frontend.sh`, Node 22, Vite dependencies and port 5173 |
| Browser request error | Start API on 127.0.0.1:8000; confirm frontend proxy |
| GitHub Actions fails without running steps | Runner/account-level problem is not evidence of failing application assertions |

## Verify before a formal demonstration

```bash
bash scripts/verify_phase8.sh --quick
bash scripts/verify_phase8.sh --full
```

The full run requires official source and model files, frontend dependencies, and free ports 8000 and 5173. It performs two system start/stop cycles; it does not substitute for inspecting the real UI on your Mac. Do not claim a successful latest benchmark until `bash scripts/verify_phase7.sh --full` passes on the current frozen experiment.

## Boundaries

Research rankings are not clinical probabilities. The app is local, not access-controlled for public use. Do not publish this development API, claim clinical safety, or use identifiable patient inputs. See `docs/PHASE_09_DISSERTATION_DRAFT.md` for the dataset and limitations.
