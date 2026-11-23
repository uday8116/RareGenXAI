"""Phase 6 official HPO/source-matched model end-to-end verification.

Run strictly (no silent skip) after preparing official Phase 2/3 artifacts:
    RAREGEN_REQUIRE_PHASE6_INTEGRATION=1 python -m pytest -q tests/test_phase6_integration.py
Never interprets HPOA disease associations as independent clinical patients.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.db_access import open_readonly

DB = Path("data/local/raregen.sqlite3")
MODEL = Path("models/raregen_ml.joblib")
REQUIRED = os.getenv("RAREGEN_REQUIRE_PHASE6_INTEGRATION") == "1"


def test_phase6_official_knowledge_explain_and_model_consistency():
    if not DB.is_file() or not MODEL.is_file():
        if REQUIRED:
            pytest.fail(
                "Phase 6 full integration needs verified data/local/raregen.sqlite3 "
                "and models/raregen_ml.joblib. Prepare Phase 2/3 before acceptance."
            )
        pytest.skip("Official HPO database and verified Phase 3 model unavailable")

    # The selected HPO term comes only from published disease annotations.
    # This is an ontology knowledge-base fixture, NOT a patient observation.
    with open_readonly(DB) as conn:
        hpo_row = conn.execute(
            """WITH RECURSIVE phenotype_terms(hpo_id) AS (
                   SELECT child_id FROM hpo_parents WHERE parent_id='HP:0000118'
                   UNION
                   SELECT p.child_id FROM hpo_parents p
                   JOIN phenotype_terms t ON p.parent_id=t.hpo_id
               )
               SELECT dp.hpo_id FROM disease_phenotypes dp
               JOIN hpo_terms ht ON ht.hpo_id = dp.hpo_id
               WHERE dp.is_negated=0 AND dp.aspect='P' AND ht.is_obsolete=0
                 AND dp.hpo_id IN (SELECT hpo_id FROM phenotype_terms)
               GROUP BY dp.hpo_id ORDER BY COUNT(DISTINCT dp.disease_id) DESC
               LIMIT 1"""
        ).fetchone()
        assert hpo_row is not None
        hpo_id = hpo_row["hpo_id"]

    payload = {
        "observations": [{"hpo_id": hpo_id, "status": "confirmed_present"}],
        "top_k": 3,
        "candidates": 40,
        "quality": True,
    }
    with TestClient(create_app(db_path=DB, model_path=MODEL)) as client:
        readiness = client.get("/api/v1/ready")
        assert readiness.status_code == 200, readiness.text
        status = client.get("/api/v1/models")
        assert status.status_code == 200
        assert status.json()["status"] == "available"
        methods = ["overlap", "semantic", "tfidf", "logistic",
                   "random_forest", "xgboost", "mlp"]
        assert all(method in status.json()["methods"] for method in methods)
        for method in methods:
            ranked_response = client.post("/api/v1/rank", json={**payload, "method": method})
            assert ranked_response.status_code == 200, (method, ranked_response.text)
            ranked = ranked_response.json()
            assert ranked["method"] == method
            assert len(ranked["results"]) <= 3
            assert len(ranked["knowledge_manifest_sha256"]) == 64
            if not ranked["results"]:
                # A legitimate empty shortlist is never filled with fake results.
                continue
            top = ranked["results"][0]
            explanation_response = client.post("/api/v1/explain", json={
                **payload, "method": method, "disease_id": top["disease_id"],
            })
            assert explanation_response.status_code == 200, (
                method, explanation_response.text
            )
            explanation = explanation_response.json()
            assert explanation["disease_id"] == top["disease_id"]
            assert explanation["method"] == method
            assert explanation["knowledge_manifest_sha256"] == ranked["knowledge_manifest_sha256"]
            assert explanation["model_sha256"] == ranked["model_sha256"]
            assert len(explanation["evidence"]) == 1
            assert explanation["evidence"][0]["hpo_id"] == hpo_id
            if method in {"overlap", "semantic"}:
                assert explanation["explanation_type"] == "signed_ontology_contributions"
                assert abs(explanation["reconstructed_baseline_score"] - top["score"]) < 1e-5
            else:
                assert explanation["explanation_type"] == "ontology_context_not_ml_attribution"
                assert explanation["reconstructed_baseline_score"] is None
                assert all(row["contribution"] is None for row in explanation["evidence"])
                assert "SHAP" in explanation["disclaimer"]
