# Phase 4 — Local FastAPI backend and API documentation

**Project:** Explainable AI-Based Classification of Rare Genetic Disorders Using Clinical Phenotypes and HPO.

**Purpose:** Read-only local HTTP endpoints between the existing Phase 2 HPO SQLite knowledge base, the verified Phase 3 trained models, and the professional frontend planned for a later phase. No AWS, Railway, hosting subscription, server rental, cloud database or Docker is needed.

## Implementation plan, in order

1. Define versioned JSON request/response contracts using Pydantic v2.
2. Expose liveness, readiness and data provenance without confusing a missing ML model with a broken API.
3. Provide HPO phenotype lookup, synonym search, disease search and full disease annotation detail.
4. Load official Phase 2 schema-v2 SQLite in read-only mode; cache public ranking resources by database snapshot.
5. Load Phase 3 trusted model and manifest only after checking the exact HPO profile and source provenance.
6. Implement candidate ranking with transparent baseline evidence contributions or ML input-feature explanations.
7. Generate OpenAPI, Swagger UI and ReDoc; allow only local frontend development CORS origins.
8. Test invalid clinical-phenotype requests, missing model, aliases, uncertainty, and document local execution.
9. Verify on Linux, an Apple Silicon GitHub runner, and an official-HPO-trained-model integration CI job.
10. Confirm final execution on the user's physical Apple M5 Mac (manual acceptance step).

## Architecture

~~~text
Local browser (future React frontend, localhost:5173)
                     |
                   JSON
                     v
 FastAPI /api/v1 — Pydantic validation / OpenAPI
                     |
                read-only service
              /                  \
      SQLite HPO v2           Trusted joblib model v2
     terms, diseases,         SHA-256 and matching
     evidence, sources         HPO source manifest
              \                  /
                candidate ranking
           score + evidence + feature values
~~~

No patient records are written to the database. The model was trained on synthetic HPO-derived disease queries, not actual patient training records. Scores are not calibrated probabilities or clinical diagnoses.

## Equipment and software

On your Apple M5 with 16 GB unified memory: Terminal, Git, Python 3.11, an activated Python virtual environment, and Homebrew libomp for XGBoost. You do not need a GPU. Internet is needed initially to install Python packages and retrieve the official HPO ontology/annotations; training and the API run locally afterwards.

## Install and run

From the repository directory:

~~~bash
git switch main
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install -r requirements.txt

# Skip these commands if the matching database/model are already verified.
python -m src.data
python -m src.knowledge_db build --replace
python -m src.knowledge_db verify --raw-dir data/raw

python -m src.train_ml --seed 42 --train-diseases 600 --test-diseases 120 --queries-per-disease 2 --candidates 40
python -m src.verify_models --raw-dir data/raw

bash scripts/start_api.sh
~~~

Back up an existing database or model before replacing it. The launch script binds to 127.0.0.1:8000, not 0.0.0.0, and disables HTTP access logs. The browser API documentation is available at:

- http://127.0.0.1:8000/docs — interactive Swagger UI
- http://127.0.0.1:8000/redoc — documentation
- http://127.0.0.1:8000/openapi.json — machine-readable OpenAPI contract

## Endpoint reference

| Verb | Path | Purpose |
| --- | --- | --- |
| GET | /api/v1/health | Liveness only (does not prove DB/model readiness) |
| GET | /api/v1/ready | SQLite readiness and optional model status |
| GET | /api/v1/knowledge/stats | Annotation counts, HPO schema and source SHA-256 hashes |
| GET | /api/v1/phenotypes/search?q=seizure&limit=20 | HPO name/ID/synonym search |
| GET | /api/v1/phenotypes/HP:0001250 | HPO term and definition; resolves alternate HPO IDs |
| GET | /api/v1/diseases/search?q=Marfan&limit=20 | Disease search |
| GET | /api/v1/diseases/MIM:154700 | Full annotation evidence and negations |
| GET | /api/v1/models | Model availability, methods and verified artifact fingerprint |
| POST | /api/v1/rank | Research disease prioritization and explanations |

### Example curl request

~~~bash
curl -s 'http://127.0.0.1:8000/api/v1/phenotypes/search?q=seizure&limit=5'

curl -s -X POST http://127.0.0.1:8000/api/v1/rank \
  -H 'Content-Type: application/json' \
  -d '{
    "method": "overlap",
    "top_k": 5,
    "quality": true,
    "observations": [
      {"hpo_id":"HP:0001250","status":"confirmed_present"},
      {"hpo_id":"HP:0001263","status":"suspected_present"}
    ]
  }'
~~~

Methods: overlap, semantic, tfidf, logistic, random_forest, xgboost, mlp. Model methods require a verified local Phase 3 saved-model pair. The default supervised shortlist has 40 TF-IDF retrieved candidates. The returned top_k is 1–20. Baselines work even when the ML artifact is missing.

Observation statuses: confirmed_present, suspected_present, confirmed_absent, unknown. A request contains 1–20 distinct HPO IDs, at least one present or suspected observation, and no patient identifier, age, hospital file or DNA data. IDs are validated and alternate identifiers are canonicalized; unknown/obsolete/duplicated IDs are rejected.

### Explanations

For overlap and semantic, each candidate has an evidence list with HPO match and weighted score contribution. For the trained models, output contains direct HPO matches, retrieval similarity, and the numerical feature inputs to the reranker. **Feature inputs are not causal SHAP explanations.** The response clearly distinguishes these two explanation types.

### Error responses

- 200 — valid success; an empty search can return an empty list.
- 404 — disease or HPO ID not found.
- 422 — invalid request, too many observations, unsupported model or observation status, duplicate/obsolete HPO IDs.
- 503 — required local database not prepared, or the requested verified ML model unavailable/incompatible.

No fallback to an untrained classifier is performed.

## Security scope

This service is for *local research demonstrations only*. It binds to loopback 127.0.0.1; the default launch script disables access logging. The API has no patient/account creation, uploads, diagnosis history or cloud calls. The SQLite file is opened read-only. CORS only permits localhost / 127.0.0.1 frontend origins on ports 5173 or 3000. CORS is not authentication. Do not bind to a public interface or use identifiable patient information: authentication, rate limiting, TLS, user consent workflows, security review and clinical privacy certifications are not in scope. Only load joblib model files you trained yourself or obtained from a trusted GitHub workflow; SHA-256 integrity alone is not a digital signature.

## Tests and acceptance criteria

~~~bash
python -m pytest -q tests/test_api.py
python -m pytest -q tests/test_api_integration.py
python -m pytest -q
~~~

Offline tests use a tiny synthetic SQLite schema-v2 fixture and do not call the internet. The second test uses the actual official HPO database and a verified trained bundle if they are present; otherwise it skips. The dedicated Phase 4 GitHub Actions job prepares HPO and the trusted model before running the real integration check and exports openapi.json as an artifact.

**Acceptance gates:** Code and contract committed; Ubuntu and macOS unit tests green; official-HPO inference integration green; full-project checks green; PR merged; finally physical Apple M5 verification. The last step cannot be completed from GitHub.

The next phase is the professional website/frontend and a model-monitoring dashboard. Phase 4 provides the backend for that frontend, not the finished website.
