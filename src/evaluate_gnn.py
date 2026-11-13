"""Train experimental HPO GNN on synthetic examples and evaluate external cases.

Optional dependency: pip install torch
Run after python -m src.data and python -m src.rarebench.
No patient case is used for model training.
"""
import argparse
import csv
import json
from pathlib import Path
from src.data import load_ontology
from src.gnn import HPOGraphReranker
from src.ranking import ontology_parents
from src.evaluate_external import read_cases, score_rank


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="data/external/rarebench_cases.csv")
    parser.add_argument("--train-diseases", type=int, default=40)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--output", default="results/gnn_external_summary.json")
    args = parser.parse_args()
    data = json.loads(Path("data/processed/profiles.json").read_text())
    model = HPOGraphReranker(data["profiles"], ontology_parents(load_ontology()), data["labels"])
    training = model.fit(train_diseases=args.train_diseases, epochs=args.epochs)
    cases = read_cases(args.cases)
    if args.max_cases:
        cases = cases[:args.max_cases]
    records = []
    for case in cases:
        observations = [(term.strip(), "confirmed_present")
                        for term in case["hpo_ids"].split(";") if term.strip()]
        ranked = model.rank(observations, k=40, top_k=None)
        position = score_rank([r["disease_id"] for r in ranked], case["disease_id"])
        records.append({"case_id": case["case_id"], "cohort": case.get("cohort", "unspecified"),
                        "rank": position or 0, "top1": int(position == 1),
                        "top5": int(position is not None and position <= 5),
                        "reciprocal_rank": 1 / position if position else 0})
    n = len(records)
    if not n:
        raise ValueError("No evaluation cases")
    result = {"method": "experimental_hpo_gnn", "n": n,
              "top1": sum(r["top1"] for r in records) / n,
              "top5": sum(r["top5"] for r in records) / n,
              "mrr": sum(r["reciprocal_rank"] for r in records) / n,
              "training": training,
              "caveat": "Synthetic training; retrospective external evaluation; graph KB overlaps case literature"}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    with path.with_name("gnn_external_cases.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
