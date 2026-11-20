"""RareGenXAI Phase 4: local-only, read-only FastAPI research backend.

Start with:
  python -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --no-access-log

The service never collects demographics or patient identifiers and never
persists observations. Do NOT bind to 0.0.0.0 or expose it to the internet.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path as URLPath, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api_schemas import (
    DiseaseDetail, DiseaseMatch, KnowledgeStats, ModelStatus,
    Phenotype, PhenotypeMatch, RankRequest, RankResponse,
    ExplainRequest, ExplainResponse,
)
from src.api_service import ResearchService
from src.db_access import (
    DEFAULT_DB, disease_detail, open_readonly, phenotype,
    search_diseases, search_phenotypes,
)
from src.ml import FEATURES
from src.ranking import rank as baseline_rank, ancestors
from src.explainability import explain_candidate as trace_candidate


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
    service = ResearchService(db_path, model_path)
    app.state.research_service = service

    def database_or_503():
        try:
            return service.context()
        except (FileNotFoundError, OSError, ValueError, sqlite3.DatabaseError) as exc:
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

    def canonical_observations(payload: RankRequest, context: dict):
        """Validate real clinical HPO findings for BOTH rank and explain.

        Excludes HPO root, inheritance categories, and nonclinical terms.
        Transient read failures return HTTP 503 rather than a traceback.
        """
        normalized, seen = [], set()
        try:
            with open_readonly(service.db_path) as conn:
                for item in payload.observations:
                    term = phenotype(conn, item.hpo_id)
                    if term is None:
                        raise HTTPException(422, "Unknown HPO ID in observations")
                    if term["is_obsolete"]:
                        raise HTTPException(422, "Obsolete HPO ID: use a current phenotype term")
                    canonical = term["hpo_id"]
                    if (canonical == "HP:0000118" or
                            "HP:0000118" not in ancestors(canonical, context["parents"])):
                        raise HTTPException(422, "HPO ID is not a clinical phenotypic abnormality")
                    if canonical in seen:
                        raise HTTPException(422, "Repeated phenotype after HPO alias normalization")
                    seen.add(canonical)
                    normalized.append((canonical, item.status))
        except (OSError, sqlite3.DatabaseError) as exc:
            raise HTTPException(503, "Local HPO knowledge changed or is temporarily unreadable") from exc
        return normalized

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
        with open_readonly(service.db_path) as conn:
            return search_phenotypes(conn, q, limit)

    @app.get(API_PREFIX + "/phenotypes/{hpo_id}", response_model=Phenotype, tags=["Phenotypes"])
    def get_phenotype(
        hpo_id: Annotated[str, URLPath(pattern=r"^HP:\d{7}$")],
    ):
        database_or_503()
        with open_readonly(service.db_path) as conn:
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
        with open_readonly(service.db_path) as conn:
            return search_diseases(conn, q, limit)

    @app.get(API_PREFIX + "/diseases/{disease_id}", response_model=DiseaseDetail, tags=["Diseases"])
    def get_disease(
        disease_id: Annotated[str, URLPath(min_length=3, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_.-]*:[A-Za-z0-9_.-]+$")],
    ):
        database_or_503()
        with open_readonly(service.db_path) as conn:
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
        normalized = canonical_observations(payload, context)
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
            "knowledge_manifest_sha256": context["knowledge_manifest_sha256"],
            "requested_count": len(normalized),
            "results": result,
            "explanation_type": explanation_type,
            "model_sha256": model_hash,
        }

    @app.post(API_PREFIX + "/explain", response_model=ExplainResponse, tags=["Explainability"])
    def explain_disease(payload: ExplainRequest):
        """Explain ontology links for one chosen candidate, not model SHAP."""
        context = database_or_503()
        if payload.disease_id not in context["profiles"]:
            raise HTTPException(404, "Disease candidate not found in the local phenotype knowledge base")
        normalized = canonical_observations(payload, context)
        manifest = None
        if payload.method not in ("overlap", "semantic"):
            _, manifest = model_or_503()
        ic = service.information_content() if payload.method == "semantic" else {}
        explanation = trace_candidate(
            normalized, payload.disease_id, context["profiles"], context["parents"], ic,
            method=payload.method, quality=payload.quality, labels=context["labels"],
        )
        if manifest is not None:
            explanation["model_sha256"] = manifest["artifact_sha256"]
        explanation["knowledge_manifest_sha256"] = context["knowledge_manifest_sha256"]
        return explanation

    return app


app = create_app()
