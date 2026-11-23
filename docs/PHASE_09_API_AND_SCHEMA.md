# Phase 9 — API, architecture and SQLite schema reference

This document describes the implemented Phase 4–8 **local research** system. The source of truth for exact route validation is `src/api.py`, `src/api_schemas.py` and its live OpenAPI schema at `http://127.0.0.1:8000/openapi.json`.

## Architecture

```text
Browser (React/Vite, 127.0.0.1:5173)
        |  local /api/v1 proxy
        v
FastAPI / Pydantic (127.0.0.1:8000)
        |  (read-only at request time)
        +--> SQLite HPO knowledge schema v2
        |      |-- phenotype ontology, aliases, parent graph
        |      +-- disease–phenotype annotations and source hashes
        +--> baseline overlap / semantic rankers
        +--> verified, trusted local joblib TF-IDF/re-rankers
                     |
                 rankings and evidence
```

**Threat boundary:** Loopback-only by default; no patient database, public authentication, hosted TLS or clinical certification. CORS is not authorization. No raw patient observations are intentionally persisted by the API; deliberate local exports must be handled carefully.

## HTTP routes

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Liveness, not data/model readiness |
| GET | `/api/v1/ready` | Knowledge database readiness and counts |
| GET | `/api/v1/knowledge/stats` | Counts, schema version and source checksums |
| GET | `/api/v1/phenotypes/search?q=seizure&limit=5` | Search term/name/synonym/ID |
| GET | `/api/v1/phenotypes/{hpo_id}` | Canonical phenotype detail |
| GET | `/api/v1/diseases/search?q=Marfan&limit=5` | Disease search |
| GET | `/api/v1/diseases/{disease_id}` | Disease evidence annotations |
| GET | `/api/v1/models` | Verified model state and available methods |
| POST | `/api/v1/rank` | Candidate-disease research ranking |
| POST | `/api/v1/explain` | Evidence trace of one candidate (not model SHAP) |

Example (uses example public HPO IDs, **not a real person**):

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s -X POST http://127.0.0.1:8000/api/v1/rank \
  -H 'Content-Type: application/json' \
  -d '{"method":"overlap","top_k":5,"observations":[{"hpo_id":"HP:0001250","status":"confirmed_present"},{"hpo_id":"HP:0001263","status":"suspected_present"}]}'
```

Request constraints: `observations` 1–20 distinct HPO IDs; each status in `confirmed_present | suspected_present | confirmed_absent | unknown`; at least one present/suspected; `top_k` 1–20; `candidates` 1–100. Supported method names are `overlap, semantic, tfidf, logistic, random_forest, xgboost, mlp`. Model-based methods require the trusted trained bundle. Unknown, obsolete, nonclinical and duplicate-after-alias-normalization IDs are rejected.

Response contracts: `/rank` returns selected `method`, `requested_count`, `results[]`, `explanation_type`, knowledge-manifest SHA-256 and optional model SHA-256. Each result contains a disease identifier, name and nonprobabilistic score, with matched evidence/features as relevant. `/explain` returns method, disease identifier/name, ontology evidence, explanation type and provenance. Neither is a diagnosis.

Typical HTTP status: 200 success, 404 unknown disease/phenotype, 422 invalid requests, 503 unavailable or incompatible local source/model. The exact current JSON shape and required fields should always be checked in live OpenAPI.

## Database v2 table dictionary

Source file: `src/db_schema.py`, `SCHEMA_VERSION = 2`.

| Table | Role and key |
|---|---|
| `schema_migrations` | Applied schema version and timestamp |
| `data_sources` | File/source URL, SHA-256 and byte count; PK filename |
| `db_metadata` | Versioned importer metadata; PK key |
| `hpo_terms` | Canonical HPO ID, name, definition, obsolete flag; PK hpo_id |
| `hpo_aliases` | Alternate ID -> canonical term; PK alias_id |
| `hpo_synonyms` | Searchable synonyms; composite PK hpo_id + synonym |
| `hpo_parents` | Child-parent ontology edges; composite PK |
| `diseases` | Disease ID/name; PK disease_id |
| `disease_phenotypes` | Unique annotation evidence, qualifier/negation, frequency, onset, sex, modifier, biocuration, source |
| `hpoa_source_rows` | Retains original source-row order and evidence, including exact duplicate source rows |

Primary relationships: `disease_phenotypes.disease_id -> diseases.disease_id`; `disease_phenotypes.hpo_id -> hpo_terms.hpo_id`; `hpo_parents` joins canonical HPO terms; `hpoa_source_rows` joins diseases and HPO terms. The schema stores curated **knowledge**, not individual patient records. Importer uses staging and versioned migrations; inference opens the approved knowledge snapshot read-only.

## Data flow and reproducibility

Official `hp.obo` + `phenotype.hpoa` -> source-manifest SHA-256 -> schema v2 SQLite -> positive HPO disease profiles -> deterministic baseline ranking or verified ML retrieval/reranking -> source-hashed UI output. The optional ML bundle is locally trusted and must match HPO/model manifests. Phase 7 freezes case set, methods, model and input hashes before a new external benchmark; historical saved predictions are a separate evidence tier.

## Verification mapping

- Schema: `src/db_schema.py`, `src/knowledge_db.py`, `tests/test_knowledge_db.py` (where present).
- API contracts: `src/api_schemas.py`, `tests/test_api.py`; live API `/openapi.json`.
- Explainability: `src/explainability.py`, `tests/test_explainability.py`.
- Research integrity: `src/phase7_experiments.py`, `tests/test_phase7_experiments.py`.
- System restart: `scripts/phase8_e2e.py`, `scripts/verify_phase8.sh`.

**Acceptance disclaimer:** configuration and documented checks do not prove current CI or on-Mac success.
