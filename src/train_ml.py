"""Train lightweight ML models and evaluate on held-out synthetic diseases."""
import argparse
import json
from pathlib import Path
from src.ml import RareGenML, write_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-diseases", type=int, default=200)
    parser.add_argument("--test-diseases", type=int, default=60)
    parser.add_argument("--queries-per-disease", type=int, default=2)
    parser.add_argument("--candidates", type=int, default=25)
    args = parser.parse_args()
    data = json.loads(Path("data/processed/profiles.json").read_text())
    ml = RareGenML(data["profiles"], data["labels"])
    rows, summary, metadata = ml.train(
        seed=args.seed, train_diseases=args.train_diseases,
        test_diseases=args.test_diseases,
        queries_per_disease=args.queries_per_disease,
        candidates=args.candidates)
    ml.save("models/raregen_ml.joblib")
    write_csv("results/ml_trials.csv", rows)
    write_csv("results/ml_summary.csv", summary)
    Path("results/ml_metadata.json").write_text(json.dumps(metadata, indent=2))
    print("ML training and disease-disjoint synthetic validation complete")
    print(json.dumps(metadata, indent=2))
    for row in summary:
        print(row)
    print("NOT clinical accuracy: synthetic cases from existing HPO annotations")


if __name__ == "__main__":
    main()
