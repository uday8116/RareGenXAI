# Phase 4 independent acceptance review — local FastAPI

**Audit date:** 19 November 2026. **Target:** local Apple M5, 16 GB RAM.
**Reviewed baseline:** `main` at `896606b` (Phase 4 PR #7).

## Summary

The original Phase 4 backend implementation was merged with all three post-merge GitHub Actions workflows passing (foundation, full-project, and dedicated FastAPI). The independent audit identified additional risks not adequately covered by the original tests.

| Audit finding | Why it matters | Implemented correction |
| --- | --- | --- |
| Loopback-only binding was only a shell-script convention | Running Uvicorn on 0.0.0.0 could expose the research API | Reject non-loopback peer addresses in ASGI middleware; restrict trusted HTTP Host headers |
| CORS could be mistaken for authentication | Browser CORS rules do not prevent direct remote HTTP calls | Actual loopback peer guard, plus explicit documentation of limitations |
| Ranking accepted ontology category headings and nonclinical HPO IDs | Inheritance modes or the ontology root are not observed phenotypic abnormalities | Accept only canonical HPO terms in the clinical phenotype subtree below HP:0000118 for ranking |
| Overlap/semantic baseline could return unrelated zero-score diseases to fill Top-k | Zero-weight results could be misconstrued as evidence for disorders | Return only candidates with positive ranking evidence; an empty list is valid |
| Database might vanish during an atomic rebuild | Unhandled read failures could lead to internal server errors | Return a controlled HTTP 503 while a read fails |
| DB/model cache key only used file size and modification time | Atomic replacement might go unnoticed if metadata was preserved | Include device, inode and creation/change-time metadata in snapshot key |
| Official integration test could silently skip | The job might appear green without ever exercising the real trained model | Require the real database/model to be present in CI; test all 7 ranking methods |
| Browser/proxy caching of research ranking responses was not prohibited | Input-derived ranking output should not be stored by caches | Add `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, and `X-Content-Type-Options: nosniff` |

## API behavior after the review

The public API routes are unchanged:

- `GET /api/v1/health`, `GET /api/v1/ready`
- `GET /api/v1/knowledge/stats`
- `GET /api/v1/phenotypes/search`, `GET /api/v1/phenotypes/{hpo_id}`
- `GET /api/v1/diseases/search`, `GET /api/v1/diseases/{disease_id}`
- `GET /api/v1/models`
- `POST /api/v1/rank`

Only **ranking observations** are restricted to non-obsolete phenotypic-abnormality descendants of `HP:0000118`. Ontology lookup/search may still return other known HPO categories; this supports research browsing without mixing categorical metadata into symptom-based classification.

The ranking endpoint no longer pads a baseline result list with zero or negative scores. A valid request with no positive evidence may return `results: []`, rather than suggesting an arbitrary disorder. This is not a diagnosis.

## HTTP status and safety

- `200`: success, including zero matches.
- `400`: untrusted Host header.
- `403`: request originated outside loopback.
- `404`: unknown ontology term or disease.
- `422`: invalid body, unknown/nonclinical/obsolete/duplicate HPO ranking observations.
- `503`: absent, incompatible or temporarily unavailable local database/model.

The provided launcher still explicitly binds Uvicorn to `127.0.0.1`. The application also rejects nonloopback TCP peers in case it is accidentally started on a wider interface. CORS only allows the planned local frontend origins; neither CORS nor the new guards constitute formal clinical privacy certification. No patient information is persisted, and identifying clinical information should not be submitted.

## Tests and CI

Offline unit tests now verify: remote peer denial, Host-header rejection, search and alias lookup, unsupported clinical HPO roots/inheritance categories, baseline no-match behavior, cache invalidation after atomic SQLite replacement, controlled 503 for mid-request file failures, and no-store headers. 

Official-data CI must prepare a schema-v2 SQLite database and a Phase 3 model manifest, then execute `overlap`, `semantic`, `tfidf`, `logistic`, `random_forest`, `xgboost`, and `mlp` through FastAPI. The environment variable `RAREGEN_REQUIRE_PHASE4_INTEGRATION=1` causes a missing database or model to fail rather than skip the required test.

The pre-review baseline CI was green:
- [Phase 4 original post-merge CI](https://github.com/uday8116/RareGenXAI/actions/runs/44516624333)
- [Full-project original post-merge CI](https://github.com/uday8116/RareGenXAI/actions/runs/44516624366)

**The review branch currently has an Actions-runner verification blocker:** new jobs across the workflows (including an unmodified baseline run) are marked failed within seconds, without any steps or available logs. This does not establish that the new test code passed or failed. Inspect the workflow's `Annotations` in GitHub Actions and verify repository Actions permission/billing/runner availability; re-run when GitHub can dispatch jobs. Do **not** mark PR #8 verified or merged solely because the original release passed.

## Manual local acceptance on your M5

~~~bash
cd RareGenXAI
git switch main
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install -r requirements.txt

# Prepare these only if not already available and verified:
python -m src.data
python -m src.knowledge_db build --replace
python -m src.train_ml --seed 42 --train-diseases 600 --test-diseases 120 --queries-per-disease 2 --candidates 40
python -m src.verify_models --raw-dir data/raw

python -m pytest -q tests/test_api.py
RAREGEN_REQUIRE_PHASE4_INTEGRATION=1 python -m pytest -q tests/test_api_integration.py
bash scripts/start_api.sh
~~~

Back up the existing database and model artifacts before rebuilding. Open `http://127.0.0.1:8000/docs`. Confirm liveness, HPO search, model status, and ranking from the interactive Swagger interface.

**Project boundary:** This is a read-only local research backend. A production website, clinical certification, authorization, patient-record persistence, diagnostic calibration and model-monitoring dashboard are outside Phase 4.
