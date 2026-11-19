"""Versioned, integrity-checked local artifact for synthetic HPO ranking models.

Only load artifacts *you trained locally* or from a trusted project CI job:
joblib uses pickle and is unsafe for untrusted model files. Hash checks detect
accidental corruption, not a malicious actor replacing both files.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
from src.ml import FEATURES, RareGenML

SCHEMA = 2
METHODS = ("tfidf", "logistic", "random_forest", "xgboost", "mlp")
PACKAGES = ("numpy", "scikit-learn", "xgboost", "joblib", "pandas")


def _digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def profile_digest(profiles: dict) -> str:
    """Deterministic fingerprint of the complete disease-to-HPO feature universe."""
    pairs = [(d, sorted(set(profiles[d]))) for d in sorted(profiles)]
    blob = json.dumps(pairs, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _witness(model: RareGenML) -> dict:
    """Small deterministic prediction signature for persistence smoke testing."""
    eligible = [d for d in model.ids if len(model.profiles[d]) >= 2]
    if not eligible:
        raise ValueError("Cannot create model witness without two phenotype terms")
    disease = eligible[0]
    observation = [(t, "confirmed_present") for t in sorted(model.profiles[disease])[:2]]
    expected = {}
    for method in METHODS:
        if method != "tfidf" and method not in model.models:
            raise ValueError(f"Missing fitted model: {method}")
        rows = model.rank(observation, model=method, k=20, top_k=3)
        if not rows:
            raise ValueError(f"Cannot create witness for {method}")
        expected[method] = [
            {"disease_id": row["disease_id"], "score": row["score"]} for row in rows
        ]
    return {"observations": observation, "rankings": expected}


def _verify_model(model: RareGenML, manifest: dict) -> None:
    if not isinstance(model, RareGenML):
        raise ValueError("Artifact is not a RareGenML bundle")
    if manifest.get("methods") != list(METHODS):
        raise ValueError("Model bundle method list mismatch")
    if manifest.get("training", {}).get("retrieval_policy") != "positive_tfidf_only_ties_by_disease_id":
        raise ValueError("Outdated retrieval policy in model bundle; retrain with Phase 3 review code")
    if manifest.get("training", {}).get("training_negative_policy") != "seeded_uniform_padding_training_only":
        raise ValueError("Outdated negative sampling policy in model bundle; retrain")
    if sorted(model.models) != sorted(METHODS[1:]):
        raise ValueError("Missing or unexpected trained estimators")
    if list(manifest.get("features", [])) != FEATURES:
        raise ValueError("Model feature schema mismatch")
    if profile_digest(model.profiles) != manifest.get("profile_sha256"):
        raise ValueError("Model profile fingerprint differs from manifest")
    witness = manifest.get("smoke_test", {})
    obs = witness.get("observations", [])
    for method in METHODS:
        actual = [
            {"disease_id": row["disease_id"], "score": row["score"]}
            for row in model.rank(obs, model=method, k=20, top_k=3)
        ]
        if actual != witness.get("rankings", {}).get(method):
            raise ValueError(f"Post-load ranking smoke test failed for {method}")


def load_verified_bundle(
    path: str | Path = "models/raregen_ml.joblib",
    *,
    expected_profiles: dict | None = None,
) -> tuple[RareGenML, dict]:
    """Verify manifest/hash before loading a **trusted local** joblib file."""
    path = Path(path)
    meta_path = path.with_suffix(".manifest.json")
    if not path.is_file() or not meta_path.is_file():
        raise FileNotFoundError(
            f"Missing model/manifest: {path} and {meta_path}. "
            "Run python -m src.train_ml"
        )
    manifest = json.loads(meta_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_schema") != SCHEMA:
        raise ValueError("Unsupported model manifest schema; retrain using the current Phase 3 code")
    if manifest.get("artifact_sha256") != _digest(path):
        raise ValueError("Model SHA-256 mismatch: file is stale or corrupted")
    if expected_profiles is not None and profile_digest(expected_profiles) != manifest.get("profile_sha256"):
        raise ValueError("Model was trained using a different HPO profile snapshot")
    # joblib/pickle can execute code. Only call for files from trusted local training.
    model = joblib.load(path)
    _verify_model(model, manifest)
    return model, manifest


def save_verified_bundle(
    model: RareGenML,
    path: str | Path,
    *,
    training: dict,
    source: dict,
) -> dict:
    """Atomically write a model and its JSON manifest, then reload and test it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta_path = path.with_suffix(".manifest.json")
    if path == meta_path:
        raise ValueError("Artifact and manifest paths must differ")
    manifest = {
        "manifest_schema": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_type": "synthetic_HPO_annotation_queries_not_patient_training",
        "non_clinical_warning": "Scores are ranking signals, NOT diagnostic probabilities",
        "training": training,
        "source": source,
        "features": list(FEATURES),
        "profile_sha256": profile_digest(model.profiles),
        "disease_universe": len(model.ids),
        "methods": list(METHODS),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": {p: importlib.metadata.version(p) for p in PACKAGES},
        },
        "smoke_test": _witness(model),
    }
    fd, tmp_name = tempfile.mkstemp(prefix=".model-", suffix=".joblib", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    json_tmp = None
    try:
        joblib.dump(model, tmp_path, compress=3)
        manifest["artifact_sha256"] = _digest(tmp_path)
        fd, json_name = tempfile.mkstemp(prefix=".model-", suffix=".json", dir=path.parent)
        json_tmp = Path(json_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
        # Validate files before publishing. A partially written pair fails closed.
        os.replace(tmp_path, path)
        os.replace(json_tmp, meta_path)
        load_verified_bundle(path, expected_profiles=model.profiles)
        return manifest
    finally:
        tmp_path.unlink(missing_ok=True)
        if json_tmp is not None:
            json_tmp.unlink(missing_ok=True)
