"""Evaluate independently sourced patient cases and optional DeepRare predictions.

Input CSV columns: case_id, disease_id, hpo_ids (semicolon-separated HP: IDs).
Optional DeepRare CSV: case_id, ranked_disease_ids (semicolon-separated IDs).
Cases must be licensed, de-identified, and independent of synthetic training.
"""
import argparse
import csv
import json
from pathlib import Path
import joblib
from src.ml import RareGenML
from src.ranking import ontology_parents, information_content, rank
from src.data import load_ontology


def read_cases(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("No cases found")
    required = {"case_id", "disease_id", "hpo_ids"}
    if not required.issubset(rows[0]):
        raise ValueError(f"Required columns: {sorted(required)}")
    if len({r["case_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate case IDs")
    return rows


def score_rank(ids, target):
    try:
        return ids.index(target) + 1
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--deeprare", default=None, help="Optional independent DeepRare predictions, same cases")
    parser.add_argument("--out", default="results/external_case_results.csv")
    parser.add_argument("--methods", nargs="+", default=["tfidf", "logistic", "random_forest", "overlap", "semantic", "quality_semantic"])
    parser.add_argument("--max-cases", type=int, default=0)
    args = parser.parse_args()
    cases = read_cases(args.cases)
    if args.max_cases > 0:
        cases = cases[:args.max_cases]
    data = json.loads(Path("data/processed/profiles.json").read_text())
    profiles = {k: set(v) for k, v in data["profiles"].items()}
    labels = data["labels"]
    ml_path = Path("models/raregen_ml.joblib")
    ml = joblib.load(ml_path) if ml_path.exists() else RareGenML(profiles, labels)
    comparison = {}
    if args.deeprare:
        with open(args.deeprare, newline="") as f:
            comparison = {r["case_id"]: r["ranked_disease_ids"].split(";") for r in csv.DictReader(f)}
        if set(comparison) != {r["case_id"] for r in cases}:
            raise ValueError("DeepRare case IDs must match exactly; no unmatched comparison allowed")
    needs_ontology = any(m in args.methods for m in ("semantic", "quality_semantic"))
    parents = ontology_parents(load_ontology()) if needs_ontology else {}
    ic = information_content(profiles, parents) if needs_ontology else {}
    records = []
    for case in cases:
        terms = [x.strip() for x in case["hpo_ids"].split(";") if x.strip()]
        if not terms:
            raise ValueError(f"Case {case['case_id']} has no HPO IDs")
        obs = [(t, "confirmed_present") for t in terms]
        for method in args.methods:
            if method in ("tfidf", "logistic", "random_forest"):
                if method != "tfidf" and method not in ml.models:
                    continue
                rows = ml.rank(obs, model=method, k=40)
            else:
                rows = rank(obs, profiles, parents, ic, labels,
                            method="overlap" if method == "overlap" else "semantic",
                            quality=(method == "quality_semantic"), top_k=len(profiles))
            ids = [row["disease_id"] for row in rows]
            position = score_rank(ids, case["disease_id"])
            known = int(case["disease_id"] in profiles)
            records.append({"case_id": case["case_id"], "cohort": case.get("cohort", "unspecified"), "method": method,
                            "true_disease_id": case["disease_id"], "known_disease": known,
                            "rank": position or "", "top1": int(position == 1),
                            "top5": int(position is not None and position <= 5),
                            "reciprocal_rank": 1 / position if position else 0})
        if comparison:
            position = score_rank(comparison[case["case_id"]], case["disease_id"])
            records.append({"case_id": case["case_id"], "cohort": case.get("cohort", "unspecified"), "method": "DeepRare_external",
                            "true_disease_id": case["disease_id"], "known_disease": known,
                            "rank": position or "",
                            "top1": int(position == 1),
                            "top5": int(position is not None and position <= 5),
                            "reciprocal_rank": 1 / position if position else 0})
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    summary = []
    for cohort in ["ALL"] + sorted({r["cohort"] for r in records}):
        for method in sorted({r["method"] for r in records}):
            subset = [r for r in records if r["method"] == method and
                      (cohort == "ALL" or r["cohort"] == cohort)]
            if not subset:
                continue
            n = len(subset)
            summary.append({"cohort": cohort, "method": method, "n": n,
                            "top1": sum(r["top1"] for r in subset) / n,
                            "top5": sum(r["top5"] for r in subset) / n,
                            "mrr": sum(r["reciprocal_rank"] for r in subset) / n,
                            "disease_coverage": sum(r["known_disease"] for r in subset) / n})
    summary_path = output.with_name("external_cohort_summary.csv")
    with summary_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    for row in summary:
        print(row)
    for method in sorted({r["method"] for r in records}):
        subset = [r for r in records if r["method"] == method]
        print(method, "n=", len(subset),
              "Top1=", round(sum(r["top1"] for r in subset) / len(subset), 4),
              "Top5=", round(sum(r["top5"] for r in subset) / len(subset), 4),
              "MRR=", round(sum(r["reciprocal_rank"] for r in subset) / len(subset), 4),
              "disease_coverage=", round(sum(r["known_disease"] for r in subset) / len(subset), 4))
    print("Patient-level external validation only if the supplied cases are independently sourced.")


if __name__ == "__main__":
    main()
