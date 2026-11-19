"""Phase 3 regression tests for training determinism and verified model artifacts."""
import json
import random
from argparse import Namespace
from pathlib import Path

import pytest

from src.ml import RareGenML
from src.model_bundle import (
    load_verified_bundle, profile_digest, save_verified_bundle,
)
from src.train_ml import train_pipeline

PROFILES = {
    f"D{i:03d}": {f"HP:{(i * 7 + j * 17) % 997 + 100:07d}" for j in range(7)}
    for i in range(32)
}


@pytest.fixture
def fitted():
    model = RareGenML(PROFILES)
    rows, summary, meta = model.train(
        seed=22, train_diseases=14, test_diseases=5,
        queries_per_disease=1, candidates=12,
    )
    return model, meta


def test_synthetic_train_holdout_is_disjoint(fitted):
    model, meta = fitted
    assert len(meta["train_disease_ids"]) == 14
    assert len(meta["heldout_disease_ids"]) == 5
    assert not set(meta["train_disease_ids"]) & set(meta["heldout_disease_ids"])
    assert meta["test_truth_never_forced_into_retrieval"] is True
    assert meta["training_pairs"] >= 14


def test_roundtrip_verifies_all_rankings_and_profiles(fitted, tmp_path):
    model, meta = fitted
    path = tmp_path / "model.joblib"
    written = save_verified_bundle(
        model, path, training=meta, source={"kind": "unit_test"},
    )
    loaded, manifest = load_verified_bundle(path, expected_profiles=model.profiles)
    assert manifest["artifact_sha256"] == written["artifact_sha256"]
    assert manifest["features"] == meta["features"]
    obs = manifest["smoke_test"]["observations"]
    assert loaded.rank(obs, model="xgboost") == model.rank(obs, model="xgboost")
    assert loaded.rank(obs, model="mlp") == model.rank(obs, model="mlp")


def test_changed_data_snapshot_rejected(fitted, tmp_path):
    model, meta = fitted
    path = tmp_path / "model.joblib"
    save_verified_bundle(model, path, training=meta, source={"kind": "unit_test"})
    altered = {key: set(values) for key, values in model.profiles.items()}
    altered["D000"].add("HP:1234567")
    with pytest.raises(ValueError, match="different HPO profile snapshot"):
        load_verified_bundle(path, expected_profiles=altered)


def test_corrupted_artifact_rejected_before_unpickling(fitted, tmp_path, monkeypatch):
    model, meta = fitted
    path = tmp_path / "model.joblib"
    save_verified_bundle(model, path, training=meta, source={"kind": "unit_test"})
    with path.open("ab") as f:
        f.write(b"corrupt")
    def unsafe_load(*args, **kwargs):
        raise AssertionError("Tampered model should never reach pickle loader")
    monkeypatch.setattr("src.model_bundle.joblib.load", unsafe_load)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_verified_bundle(path)


def test_missing_manifest_rejected(fitted, tmp_path):
    model, meta = fitted
    path = tmp_path / "model.joblib"
    save_verified_bundle(model, path, training=meta, source={"kind": "unit_test"})
    path.with_suffix(".manifest.json").unlink()
    with pytest.raises(FileNotFoundError, match="Missing model/manifest"):
        load_verified_bundle(path)


def test_fingerprint_is_order_independent():
    reversed_profiles = dict(reversed(list(PROFILES.items())))
    assert profile_digest(PROFILES) == profile_digest(reversed_profiles)


def test_training_pipeline_legacy_json_and_saved_outputs(tmp_path):
    file = tmp_path / "profiles.json"
    file.write_text(json.dumps({
        "profiles": {key: sorted(terms) for key, terms in PROFILES.items()},
        "labels": {key: key for key in PROFILES},
    }))
    args = Namespace(
        seed=11, train_diseases=12, test_diseases=4,
        queries_per_disease=1, candidates=10, data_source="legacy-json",
        db=tmp_path / "unused.sqlite3", profiles=file,
        output=tmp_path / "models" / "model.joblib",
        results_dir=tmp_path / "results",
    )
    manifest = train_pipeline(args)
    loaded, _ = load_verified_bundle(args.output)
    assert len(loaded.models) == 4
    assert manifest["training"]["source_kind"] == "legacy_json_all_aspects"
    assert (args.results_dir / "ml_trials.csv").exists()
    assert len(manifest["training"]["heldout_disease_ids"]) == 4


def test_bad_training_sizes_rejected():
    model = RareGenML(PROFILES)
    with pytest.raises(ValueError, match="positive integers"):
        model.train(train_diseases=0)
