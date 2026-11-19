"""Train + persist CPU-friendly HPO models with trusted provenance and reload checks.

Default input: the Phase 2 schema-v2 SQLite knowledge base (phenotypic aspect P).
The four supervised rerankers learn only from synthetic HPO-derived queries.
A whole-disease holdout is synthetic validation, NOT clinical accuracy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.db_access import open_readonly, load_ranking_inputs, stats
from src.knowledge_db import validate_connection
from src.ml import RareGenML, write_csv
from src.model_bundle import save_verified_bundle, load_verified_bundle, profile_digest


def train_pipeline(args: argparse.Namespace) -> dict:
    if min(args.train_diseases, args.test_diseases, args.queries_per_disease, args.candidates) <= 0:
        raise ValueError("Training sizes, queries per disease, and candidates must be > 0")
    if args.data_source == "sqlite":
        with open_readonly(args.db) as conn:
            source_stats = validate_connection(conn)
            profiles, _, labels, _ = load_ranking_inputs(conn, phenotypic_only=True)
        source = {
            "kind": "hpo_sqlite_v2_aspect_P",
            "data_sources": source_stats["sources"],
            "schema_version": source_stats["metadata"]["schema_version"],
            "annotation_rows": source_stats["metadata"]["annotation_rows_read"],
        }
    else:
        path = Path(args.profiles)
        document = json.loads(path.read_text(encoding="utf-8"))
        profiles = {d: set(p) for d, p in document["profiles"].items() if p}
        labels = document["labels"]
        source = {
            "kind": "legacy_json_all_aspects",
            "profiles_path": str(path),
            "note": "Prior prototype data: may include non-phenotypic aspects",
        }
    model = RareGenML(profiles, labels)
    details, summary, metadata = model.train(
        seed=args.seed,
        train_diseases=args.train_diseases,
        test_diseases=args.test_diseases,
        queries_per_disease=args.queries_per_disease,
        candidates=args.candidates,
    )
    if not details or not summary:
        raise ValueError("No synthetic evaluation cases generated")
    metadata["source_kind"] = source["kind"]
    metadata["profile_sha256"] = profile_digest(model.profiles)
    metadata["metrics_scope"] = "synthetic_heldout_diseases_only_not_patient_accuracy"
    results = Path(args.results_dir)
    results.mkdir(parents=True, exist_ok=True)
    write_csv(results / "ml_trials.csv", details)
    write_csv(results / "ml_summary.csv", summary)
    (results / "ml_metadata.json").write_text(json.dumps(
        {"training": metadata, "source": source}, indent=2, sort_keys=True
    ) + "\n", encoding="utf-8")
    manifest = save_verified_bundle(model, args.output, training=metadata, source=source)
    reloaded, _ = load_verified_bundle(args.output, expected_profiles=profiles)
    if reloaded.ids != model.ids:
        raise AssertionError("Reloaded candidate universe does not match training")
    print("Trained TF-IDF + Logistic Regression, Random Forest, XGBoost and MLP.")
    print("Verified model reload, artifact SHA-256, source profile hash and model predictions.")
    print("Synthetic held-out disease validation; NOT independent patient accuracy.")
    print(json.dumps({
        "model_file": str(args.output),
        "manifest": str(Path(args.output).with_suffix(".manifest.json")),
        "sha256": manifest["artifact_sha256"],
        "seed": args.seed,
        "train_diseases": metadata["train_diseases"],
        "heldout_diseases": metadata["heldout_diseases"],
        "training_pairs": metadata["training_pairs"],
        "training_features_sha256": metadata["training_feature_matrix_sha256"],
        "validation_kind": metadata["validation_kind"],
    }, indent=2))
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--train-diseases", type=int, default=600)
    p.add_argument("--test-diseases", type=int, default=120)
    p.add_argument("--queries-per-disease", type=int, default=2)
    p.add_argument("--candidates", type=int, default=40)
    p.add_argument("--data-source", choices=("sqlite", "legacy-json"), default="sqlite")
    p.add_argument("--db", type=Path, default=Path("data/local/raregen.sqlite3"))
    p.add_argument("--profiles", type=Path, default=Path("data/processed/profiles.json"))
    p.add_argument("--output", type=Path, default=Path("models/raregen_ml.joblib"))
    p.add_argument("--results-dir", type=Path, default=Path("results"))
    train_pipeline(p.parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
