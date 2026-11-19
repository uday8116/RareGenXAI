"""Integration test using prepared official HPO data and Phase 3 model."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.db_access import open_readonly

DB = Path("data/local/raregen.sqlite3")
MODEL = Path("models/raregen_ml.joblib")


@pytest.mark.skipif(not DB.exists() or not MODEL.exists(),
                    reason="Official HPO database and trained model not prepared")
def test_official_hpo_and_trained_ml_through_local_api():
    with open_readonly(DB) as conn:
        row = conn.execute(
            """SELECT hpo_id FROM disease_phenotypes
               WHERE is_negated=0 AND aspect='P'
               GROUP BY hpo_id ORDER BY COUNT(DISTINCT disease_id) DESC LIMIT 1"""
        ).fetchone()
    assert row is not None
    hpo_id = row["hpo_id"]
    with TestClient(create_app(db_path=DB, model_path=MODEL)) as client:
        ready = client.get("/api/v1/ready")
        assert ready.status_code == 200, ready.text
        assert ready.json()["model_status"] == "available"
        installed = client.get("/api/v1/models")
        assert installed.status_code == 200
        assert installed.json()["manifest_schema"] == 2
        for method in ("overlap", "tfidf", "xgboost"):
            response = client.post("/api/v1/rank", json={
                "method": method, "top_k": 3,
                "observations": [{"hpo_id": hpo_id, "status": "confirmed_present"}],
            })
            assert response.status_code == 200, (method, response.text)
            ranked = response.json()
            assert ranked["method"] == method
            assert ranked["results"]
            assert len(ranked["results"]) <= 3
        assert client.get("/api/v1/phenotypes/" + hpo_id).json()["hpo_id"] == hpo_id
