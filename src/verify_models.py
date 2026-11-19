"""Verify trained model provenance, exact data snapshot and synthetic trial files.

Only load artifacts trained locally or obtained from a trusted GitHub workflow.
Joblib (pickle) is unsafe for files from untrusted sources.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from src.db_access import open_readonly, load_ranking_inputs
from src.knowledge_db import validate_connection
from src.model_bundle import METHODS, load_verified_bundle, profile_digest
from src.evaluation_integrity import audit_synthetic_results


def verify_models(
    *,
    model_path: str | Path = "models/raregen_ml.joblib",
    db_path: str | Path = "data/local/raregen.sqlite3",
    raw_dir: str | Path | None = None,
    results_dir: str | Path = "results",
) -> dict:
    with open_readonly(db_path) as conn:
        db = validate_connection(conn, raw_dir=Path(raw_dir) if raw_dir else None)
        profiles, _, _, _ = load_ranking_inputs(conn, phenotypic_only=True)
    model, manifest = load_verified_bundle(model_path, expected_profiles=profiles)
    if manifest.get("source", {}).get("kind") != "hpo_sqlite_v2_aspect_P":
        raise ValueError("This verifier requires the Phase 2 phenotype-only SQLite dataset")
    if manifest["source"].get("data_sources") != db["sources"]:
        raise ValueError("Source URL/size/SHA-256 mismatch between model and database")
    train = manifest.get("training", {})
    if train.get("source_kind") != manifest["source"]["kind"]:
        raise ValueError("Training source identifier mismatch")
    training = set(train.get("train_disease_ids", []))
    heldout = set(train.get("heldout_disease_ids", []))
    if (not training or not heldout or training & heldout or
            len(training) != train.get("train_diseases") or
            len(heldout) != train.get("heldout_diseases")):
        raise ValueError("Synthetic training and held-out disease splits are not disjoint")
    if not (training | heldout).issubset(set(model.ids)):
        raise ValueError("Training/evaluation IDs missing from bundled model universe")
    if not re.fullmatch(r"[a-f0-9]{64}", str(train.get("training_feature_matrix_sha256", ""))):
        raise ValueError("Missing/invalid training matrix fingerprint")
    if train.get("profile_sha256") != profile_digest(profiles):
        raise ValueError("Recorded HPO profile fingerprint mismatch")

    results_dir = Path(results_dir)
    meta_file = results_dir / "ml_metadata.json"
    summary_file = results_dir / "ml_summary.csv"
    trial_file = results_dir / "ml_trials.csv"
    metadata = json.loads(meta_file.read_text(encoding="utf-8"))
    if metadata.get("training") != train or metadata.get("source") != manifest["source"]:
        raise ValueError("Training metadata does not match model bundle")
    with summary_file.open(newline="", encoding="utf-8") as f:
        summary = list(csv.DictReader(f))
    with trial_file.open(newline="", encoding="utf-8") as f:
        trials = list(csv.DictReader(f))
    audited = audit_synthetic_results(summary, trials, heldout)
    if train.get("retrieval_policy") != "positive_tfidf_only_ties_by_disease_id":
        raise ValueError("Model manifest does not record the reviewed retrieval policy")
    if train.get("training_negative_policy") != "seeded_uniform_padding_training_only":
        raise ValueError("Model manifest does not record the reviewed negative-sampling policy")
    return {
        "status": "verified",
        "model_artifact": str(model_path),
        "manifest": str(Path(model_path).with_suffix(".manifest.json")),
        "disease_universe": len(model.ids),
        "trained_methods": list(model.models),
        "train_diseases": len(training),
        "heldout_diseases": len(heldout),
        "synthetic_trial_rows": audited["trial_rows"],
        "audited_summary_rows": audited["summary_rows"],
        "model_sha256": manifest["artifact_sha256"],
        "profile_sha256": manifest["profile_sha256"],
        "training_features_sha256": train["training_feature_matrix_sha256"],
        "warning": "Synthetic HPO validation, NOT verified clinical diagnostic accuracy",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/raregen_ml.joblib")
    parser.add_argument("--db", default="data/local/raregen.sqlite3")
    parser.add_argument("--raw-dir", default=None)
    parser.add_argument("--results-dir", default="results")
    args = parser.parse_args(argv)
    report = verify_models(
        model_path=args.model,
        db_path=args.db,
        raw_dir=args.raw_dir,
        results_dir=args.results_dir,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
