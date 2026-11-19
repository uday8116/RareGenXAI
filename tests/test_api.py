"""Offline Phase 4 FastAPI unit tests. No downloads, patients or model fitting."""
from __future__ import annotations

import sqlite3
import os
import shutil

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.db_schema import apply_migrations
from src.ml import FEATURES


@pytest.fixture
def client(tmp_path):
    path = tmp_path / "research.sqlite3"
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        apply_migrations(conn)
        conn.executemany(
            "INSERT INTO hpo_terms(hpo_id,name,definition,is_obsolete) VALUES (?,?,?,?)",
            [
                ("HP:0000001", "All", "", 0),
                ("HP:0000006", "Autosomal dominant inheritance", "", 0),
                ("HP:0000118", "Phenotypic abnormality", "", 0),
                ("HP:0001250", "Seizure", "A clinical phenotype", 0),
                ("HP:0001263", "Global developmental delay", "", 0),
                ("HP:0008000", "Unused phenotype", "", 0),
                ("HP:0999999", "Old term", "", 1),
            ],
        )
        conn.execute(
            "INSERT INTO hpo_aliases(alias_id,hpo_id) VALUES ('HP:0099999','HP:0001250')"
        )
        conn.execute(
            "INSERT INTO hpo_synonyms(hpo_id,synonym) VALUES ('HP:0001250','Convulsion')"
        )
        conn.executemany("INSERT INTO hpo_parents(child_id,parent_id) VALUES (?,?)", [
            ("HP:0001250", "HP:0000118"), ("HP:0001263", "HP:0000118"),
            ("HP:0008000", "HP:0000118"),
            ("HP:0000118", "HP:0000001"),
            ("HP:0000006", "HP:0000001"),
        ])
        conn.executemany(
            "INSERT INTO diseases(disease_id,name) VALUES (?,?)",
            [("MIM:1234", "Example syndrome A"), ("ORPHA:10", "Example syndrome B")],
        )
        annotations = [
            ("MIM:1234", "HP:0001250", 0, "P"),
            ("MIM:1234", "HP:0001263", 1, "P"),
            ("ORPHA:10", "HP:0001250", 0, "P"),
            ("ORPHA:10", "HP:0001263", 0, "P"),
        ]
        for number, (disease, hpo, negated, aspect) in enumerate(annotations, 1):
            conn.execute(
                "INSERT INTO disease_phenotypes(disease_id,hpo_id,is_negated,aspect) VALUES (?,?,?,?)",
                (disease, hpo, negated, aspect),
            )
            conn.execute(
                """INSERT INTO hpoa_source_rows(
                       row_number,disease_id,disease_name,raw_hpo_id,hpo_id,qualifier,aspect)
                   VALUES (?,?,?,?,?,?,?)""",
                (number, disease, "Example syndrome", hpo, hpo,
                 "NOT" if negated else "", aspect),
            )
        conn.executemany(
            "INSERT INTO data_sources(filename,source_url,sha256,byte_count) VALUES (?,?,?,?)",
            [
                ("hp.obo", "https://example.invalid/hp.obo", "a" * 64, 1024),
                ("phenotype.hpoa", "https://example.invalid/phenotype.hpoa", "b" * 64, 2048),
            ],
        )
        conn.executemany(
            "INSERT INTO db_metadata(key,value) VALUES (?,?)",
            [("schema_version", "2"), ("annotation_rows_read", "4"),
             ("duplicate_annotations", "0"), ("unmapped_annotations", "0")],
        )
        conn.commit()
    finally:
        conn.close()
    app = create_app(db_path=path, model_path=tmp_path / "untrained.joblib")
    with TestClient(app) as test_client:
        yield test_client


def test_local_liveness_without_database(tmp_path):
    app = create_app(db_path=tmp_path / "absent.sqlite3",
                     model_path=tmp_path / "absent.joblib")
    with TestClient(app) as test_client:
        assert test_client.get("/api/v1/health").json()["status"] == "ok"
        unavailable = test_client.get("/api/v1/ready")
        assert unavailable.status_code == 503
        assert "knowledge" in unavailable.json()["detail"].lower()


def test_database_readiness_and_provenance(client):
    ready = client.get("/api/v1/ready")
    assert ready.status_code == 200
    assert ready.json()["disease_count"] == 2
    assert ready.json()["model_status"] == "missing"
    stats = client.get("/api/v1/knowledge/stats").json()
    assert stats["schema_version"] == "2"
    assert stats["counts"]["hpo_terms"] == 7
    assert len(stats["sources"]) == 2


def test_phenotype_search_alias_synonym_and_validation(client):
    records = client.get("/api/v1/phenotypes/search", params={"q": "Convulsion"}).json()
    assert records[0]["hpo_id"] == "HP:0001250"
    alias = client.get("/api/v1/phenotypes/HP:0099999")
    assert alias.status_code == 200
    assert alias.json()["hpo_id"] == "HP:0001250"
    assert client.get("/api/v1/phenotypes/HP:9999999").status_code == 404
    assert client.get("/api/v1/phenotypes/BAD").status_code == 422
    assert client.get("/api/v1/phenotypes/search", params={"q": "%"}).status_code == 422
    assert client.get("/api/v1/phenotypes/search", params={"q": "a", "limit": 101}).status_code == 422


def test_disease_search_and_full_annotation_detail(client):
    found = client.get("/api/v1/diseases/search", params={"q": "syndrome"}).json()
    assert len(found) == 2
    result = client.get("/api/v1/diseases/MIM:1234")
    assert result.status_code == 200
    info = result.json()
    assert info["name"] == "Example syndrome A"
    assert any(row["is_negated"] == 1 for row in info["phenotypes"])
    assert client.get("/api/v1/diseases/MIM:404").status_code == 404


def test_rank_overlap_explanations_canonicalization(client):
    response = client.post("/api/v1/rank", json={
        "method": "overlap",
        "observations": [{"hpo_id": "HP:0099999", "status": "confirmed_present"}],
        "top_k": 2,
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["results"]) == 2
    assert result["explanation_type"] == "per_phenotype_score_contributions"
    assert result["results"][0]["matched_hpo"] == ["HP:0001250"]
    assert result["results"][0]["evidence"][0]["hpo_id"] == "HP:0001250"
    assert result["model_sha256"] is None
    assert "not calibrated" in result["disclaimer"].lower()
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_semantic_and_negative_observation(client):
    response = client.post("/api/v1/rank", json={
        "method": "semantic",
        "top_k": 2,
        "observations": [
            {"hpo_id": "HP:0001250", "status": "suspected_present"},
            {"hpo_id": "HP:0001263", "status": "confirmed_absent"},
        ],
    })
    assert response.status_code == 200, response.text
    assert 0 < len(response.json()["results"]) <= 2
    assert all(row["score"] > 0 for row in response.json()["results"])
    assert all("contribution" in e for r in response.json()["results"] for e in r["evidence"])


@pytest.mark.parametrize("observations", [
    [{"hpo_id": "HP:0001250", "status": "invalid"}],
    [{"hpo_id": "HP:0001250", "status": "unknown"}],
    [{"hpo_id": "HP:0001250", "status": "confirmed_absent"}],
    [{"hpo_id": "HP:0001250", "status": "confirmed_present"},
     {"hpo_id": "HP:0001250", "status": "suspected_present"}],
    [{"hpo_id": "HP:0001250", "status": "confirmed_present"},
     {"hpo_id": "HP:0099999", "status": "suspected_present"}],
    [{"hpo_id": "HP:0999999", "status": "confirmed_present"}],
    [{"hpo_id": "HP:9999999", "status": "confirmed_present"}],
])
def test_reject_invalid_observations(client, observations):
    assert client.post("/api/v1/rank", json={"observations": observations}).status_code == 422


def test_missing_model_fails_closed_and_baseline_still_runs(client):
    assert client.get("/api/v1/models").json()["status"] == "missing"
    denied = client.post("/api/v1/rank", json={
        "method": "xgboost",
        "observations": [{"hpo_id": "HP:0001250", "status": "confirmed_present"}],
    })
    assert denied.status_code == 503
    assert client.post("/api/v1/rank", json={
        "method": "overlap",
        "observations": [{"hpo_id": "HP:0001250", "status": "confirmed_present"}],
    }).status_code == 200


def test_verified_model_inference_returns_features_not_fake_shap(client, monkeypatch):
    service = client.app.state.research_service

    class TrainedStub:
        profiles = {"MIM:1234": {"HP:0001250"}}

        def rank(self, observations, model, k, top_k):
            assert model == "xgboost"
            return [{
                "disease_id": "MIM:1234", "disease_name": "Example syndrome A",
                "score": 0.83, "retrieval_similarity": 0.62,
                "matched_hpo": ["HP:0001250"],
            }]

        def features(self, observations, disease, similarity):
            return np.array([similarity, 1, 0, 1, 0, 0.125, 0.01])

    monkeypatch.setattr(
        service, "verified_model",
        lambda: (TrainedStub(), {"artifact_sha256": "c" * 64}),
    )
    result = client.post("/api/v1/rank", json={
        "method": "xgboost",
        "observations": [{"hpo_id": "HP:0001250", "status": "confirmed_present"}],
    })
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["explanation_type"] == "matched_terms_and_feature_values"
    assert body["model_sha256"] == "c" * 64
    assert list(body["results"][0]["features"]) == FEATURES
    assert body["results"][0]["evidence"][0]["match"] == 1.0


def test_openapi_and_local_cors(client):
    openapi = client.get("/openapi.json").json()
    assert "/api/v1/rank" in openapi["paths"]
    assert "/api/v1/models" in openapi["paths"]
    assert client.get("/docs").status_code == 200
    allowed = client.options("/api/v1/rank", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    })
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    blocked = client.options("/api/v1/rank", headers={
        "Origin": "https://other.example.com",
        "Access-Control-Request-Method": "POST",
    })
    assert "access-control-allow-origin" not in blocked.headers



def test_reject_nonclinical_hpo_ids_even_when_present_in_ontology(client):
    for hpo_id in ("HP:0000001", "HP:0000006", "HP:0000118"):
        response = client.post("/api/v1/rank", json={
            "method": "overlap",
            "observations": [{"hpo_id": hpo_id, "status": "confirmed_present"}],
        })
        assert response.status_code == 422, response.text
        assert "clinical phenotypic" in response.json()["detail"]


def test_zero_score_baseline_does_not_offer_unrelated_diseases(client):
    response = client.post("/api/v1/rank", json={
        "method": "overlap",
        "observations": [
            {"hpo_id": "HP:0008000", "status": "confirmed_present"},
        ],
    })
    assert response.status_code == 200, response.text
    assert response.json()["results"] == []


def test_local_network_restrictions_even_if_server_is_exposed(client):
    from fastapi.testclient import TestClient

    assert client.get("/api/v1/health").status_code == 200
    bad_host = client.get("/api/v1/health", headers={"host": "untrusted.example"})
    assert bad_host.status_code == 400
    with TestClient(client.app, client=("198.51.100.43", 44120)) as remote:
        denied = remote.get("/api/v1/health")
        assert denied.status_code == 403
        assert "local-only" in denied.json()["detail"].lower()


def test_database_open_failure_mid_request_returns_service_unavailable(client, monkeypatch):
    # Warm the public-knowledge cache first so a later read uses it.
    assert client.get("/api/v1/ready").status_code == 200

    def disappear(*args, **kwargs):
        raise FileNotFoundError("simulated atomic replacement interval")

    monkeypatch.setattr("src.api.open_readonly", disappear)
    response = client.get("/api/v1/phenotypes/search", params={"q": "seizure"})
    assert response.status_code == 503
    assert "database" in response.json()["detail"].lower()


def test_database_snapshot_key_changes_on_atomic_file_replacement(client, tmp_path):
    service = client.app.state.research_service
    before = service.context()
    old_key = service._file_key(service.db_path)
    staged = tmp_path / "replacement.sqlite3"
    shutil.copy2(service.db_path, staged)
    os.replace(staged, service.db_path)
    new_key = service._file_key(service.db_path)
    assert new_key != old_key
    after = service.context()
    assert after is not before
    assert after["counts"]["hpo_terms"] == before["counts"]["hpo_terms"]
