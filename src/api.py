"""RareGenXAI Phase 4: local-only, read-only FastAPI research backend.

Start with:
  python -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --no-access-log

The service never collects demographics or patient identifiers and never
persists observations. Do NOT bind to 0.0.0.0 or expose it to the internet.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from ipaddress import ip_address
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path as URLPath, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.api_schemas import (
    DiseaseDetail, DiseaseMatch, KnowledgeStats, ModelStatus,
    Phenotype, PhenotypeMatch, RankRequest, RankResponse,
)
from src.api_service import ResearchService
from src.db_access import (
    DEFAULT_DB, disease_detail, open_readonly, phenotype,
    search_diseases, search_phenotypes,
)
from src.ml import FEATURES
from src.ranking import ancestors, rank as baseline_rank


API_PREFIX = "/api/v1"
LOCAL_CORS = ("http://127.0.0.1:5173", "http://localhost:5173",
              "http://127.0.0.1:3000", "http://localhost:3000")


def create_app(
    *,
    db_path: str | Path = DEFAULT_DB,
    model_path: str | Path = "models/raregen_ml.joblib",
) -> FastAPI:
    app = FastAPI(
        title="RareGenXAI Local Research API",
        version="1.0.0",
        description=(
            "HPO phenotype search, local rare-disease knowledge and explainable "
            "candidate ranking. Research only; NOT a clinical diagnostic system. "
            "No patient data is persisted."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=list(LOCAL_CORS),
        allow_credentials=False, allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"], max_age=600,
    )
    # CORS only controls browsers; these guards enforce local-only access
    # even if uvicorn is accidentally started with --host 0.0.0.0.
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "testserver"],
    )

    @app.middleware("http")
    async def restrict_to_loopback(request: Request, call_next):
        peer = request.client.host if request.client else None
        if peer != "testclient":
            try:
                allowed = peer is not None and ip_address(peer).is_loopback
            except ValueError:
                allowed = False
            if not allowed:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Local-only research API: remote clients are not allowed"},
                )
        return await call_next(request)

    service = ResearchService(db_path, model_path)
    app.state.research_service = service

    def database_or_503():
        try:
            return service.context()
        except (FileNotFoundError, OSError, ValueError, KeyError, TypeError, sqlite3.DatabaseError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Local HPO knowledge unavailable. Run python -m src.data and python -m src.knowledge_db build",
            ) from exc

    def model_or_503():
        try:
            return service.verified_model()
        except (FileNotFoundError, OSError, ValueError, KeyError, TypeError, sqlite3.DatabaseError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Verified local trained model unavailable or incompatible. Run python -m src.train_ml",
            ) from exc

    @contextmanager
    def read_connection():
        """Return 503 (not a leaking trace) when the DB changes mid-request."""
        try:
            with open_readonly(service.db_path) as conn:
                yield conn
        except (FileNotFoundError, OSError, sqlite3.DatabaseError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Local HPO database is unavailable during this request",
            ) from exc

    @app.get(API_PREFIX + "/health", tags=["System"])
    def health():
        """Liveness probe: does not claim models or HPO data are installed."""
        return {"status": "ok", "api_version": "v1", "service": "RareGenXAI"}

    @app.get(API_PREFIX + "/ready", tags=["System"])
    def ready():
        """The knowledge-based methods work even without optional ML model files."""
        context = database_or_503()
        return {
            "ready": True,
            "knowledge_schema": context["schema_version"],
            "phenotype_count": context["counts"]["hpo_terms"],
            "disease_count": context["counts"]["diseases"],
            "model_status": service.model_status()["status"],
            "note": "Baseline ranking can run without trained ML model weights.",
        }

    @app.get(API_PREFIX + "/knowledge/stats", response_model=KnowledgeStats, tags=["Knowledge"])
    def knowledge_stats():
        context = database_or_503()
        return {
            "counts": context["counts"],
            "schema_version": context["schema_version"],
            "sources": context["sources"],
        }

    @app.get(API_PREFIX + "/phenotypes/search", response_model=list[PhenotypeMatch], tags=["Phenotypes"])
    def find_phenotypes(
        q: Annotated[str, Query(min_length=2, max_length=80, description="Phenotype term, synonym or HPO ID")],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ):
        database_or_503()
        with read_connection() as conn:
            return search_phenotypes(conn, q, limit)

    @app.get(API_PREFIX + "/phenotypes/{hpo_id}", response_model=Phenotype, tags=["Phenotypes"])
    def get_phenotype(
        hpo_id: Annotated[str, URLPath(pattern=r"^HP:\d{7}$")],
    ):
        database_or_503()
        with read_connection() as conn:
            found = phenotype(conn, hpo_id)
        if found is None:
            raise HTTPException(404, "HPO ID not found in the local ontology")
        return found

    @app.get(API_PREFIX + "/diseases/search", response_model=list[DiseaseMatch], tags=["Diseases"])
    def find_diseases(
        q: Annotated[str, Query(min_length=2, max_length=80)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ):
        database_or_503()
        with read_connection() as conn:
            return search_diseases(conn, q, limit)

    @app.get(API_PREFIX + "/diseases/{disease_id}", response_model=DiseaseDetail, tags=["Diseases"])
    def get_disease(
        disease_id: Annotated[str, URLPath(min_length=3, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_.-]*:[A-Za-z0-9_.-]+$")],
    ):
        database_or_503()
        with read_connection() as conn:
            found = disease_detail(conn, disease_id)
        if found is None:
            raise HTTPException(404, "Disease ID not found in the local annotations")
        return found

    @app.get(API_PREFIX + "/models", response_model=ModelStatus, tags=["Models"])
    def models():
        database_or_503()
        return service.model_status()

    @app.post(API_PREFIX + "/rank", response_model=RankResponse, tags=["Ranking"])
    def rank_diseases(payload: RankRequest):
        """Return ranked research candidates, never probabilities or a diagnosis."""
        context = database_or_503()
        normalized = []
        seen = set()
        with read_connection() as conn:
            for item in payload.observations:
                term = phenotype(conn, item.hpo_id)
                if term is None:
                    raise HTTPException(422, "Unknown HPO ID in observations")
                if term["is_obsolete"]:
                    raise HTTPException(422, "Obsolete HPO ID: use a current phenotype term")
                canonical = term["hpo_id"]
                # Only actual clinical phenotype terms under HP:0000118 are
                # eligible for disease ranking. Inheritance/mode of transmission
                # and ontology root headings are not patient symptom findings.
                if (canonical == "HP:0000118" or
                        "HP:0000118" not in ancestors(canonical, context["parents"])):
                    raise HTTPException(
                        422, "HPO ID is not a clinical phenotypic abnormality"
                    )
                if canonical in seen:
                    raise HTTPException(422, "Repeated phenotype after HPO alias normalization")
                seen.add(canonical)
                normalized.append((canonical, item.status))
        positive = {t for t, s in normalized if s in ("confirmed_present", "suspected_present")}
        result = []
        model_hash = None

        if payload.method in ("overlap", "semantic"):
            ic = service.information_content() if payload.method == "semantic" else {}
            rows = baseline_rank(
                normalized, context["profiles"], context["parents"], ic,
                context["labels"], method=payload.method,
                quality=payload.quality, top_k=payload.top_k,
            )
            for row in rows:
                # Baselines otherwise return unrelated zero/negative-score
                # candidates merely to fill top_k. Do not imply a disease
                # match when there is no positive ranking evidence.
                if row["score"] <= 0:
                    continue
                matches = sorted(positive & context["profiles"].get(row["disease_id"], set()))
                result.append({
                    "disease_id": row["disease_id"],
                    "disease_name": row["disease_name"],
                    "score": row["score"],
                    "matched_hpo": matches,
                    "evidence": row["evidence"],
                })
            explanation_type = "per_phenotype_score_contributions"
        else:
            model, manifest = model_or_503()
            rows = model.rank(
                normalized, model=payload.method,
                k=payload.candidates, top_k=payload.top_k,
            )
            for row in rows:
                # Features are model inputs, NOT causal SHAP explanations.
                inputs = model.features(
                    normalized, row["disease_id"], row["retrieval_similarity"]
                )
                result.append({
                    **row,
                    "evidence": [
                        {"hpo_id": hpo, "status": status,
                         "match": float(hpo in model.profiles[row["disease_id"]])}
                        for hpo, status in normalized if status != "unknown"
                    ],
                    "features": {name: float(value) for name, value in zip(FEATURES, inputs)},
                })
            explanation_type = "matched_terms_and_feature_values"
            model_hash = manifest["artifact_sha256"]
        return {
            "method": payload.method,
            "requested_count": len(normalized),
            "results": result,
            "explanation_type": explanation_type,
            "model_sha256": model_hash,
        }

    return app


app = create_app()
