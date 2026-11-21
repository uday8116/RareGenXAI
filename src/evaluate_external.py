"""Evaluate independently sourced patient cases and optional DeepRare predictions.

Input CSV columns: case_id, disease_id, hpo_ids (semicolon-separated HP: IDs).
Optional DeepRare CSV: case_id, ranked_disease_ids (semicolon-separated IDs).
Cases must be licensed, de-identified, and independent of synthetic training.
"""
import argparse
import csv
from pathlib import Path
from src.model_bundle import load_verified_bundle
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
    case_ids = [str(r.get("case_id", "")).strip() for r in rows]
    if not all(case_ids) or len(set(case_ids)) != len(rows):
        raise ValueError("Empty or duplicate case IDs")
    for record in rows:
        if not str(record.get("disease_id", "")).strip() or not str(record.get("hpo_ids", "")).strip():
            raise ValueError("Cases must have nonempty disease IDs and HPO terms")
    return rows


def score_rank(ids, target):
    try:
        return ids.index(target) + 1
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--model", default="models/raregen_ml.joblib", help="Trusted local model bundle")
    parser.add_argument("--deeprare", default=None, help="Optional independent DeepRare predictions, same cases")
    parser.add_argument("--out", default="results/external_case_results.csv")
    parser.add_argument("--methods", nargs="+", default=["tfidf", "logistic", "random_forest", "xgboost", "mlp", "overlap", "semantic", "quality_semantic"])
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--retrieval-k", type=int, default=40, help="Pre-registered TF-IDF candidate shortlist size")
    args = parser.parse_args()
    if args.retrieval_k <= 0:
        raise ValueError("--retrieval-k must be positive")
    allowed = {"tfidf", "logistic", "random_forest", "xgboost", "mlp",
               "overlap", "semantic", "quality_semantic"}
    if not args.methods or any(m not in allowed for m in args.methods):
        raise ValueError(f"Invalid model method; choose from {sorted(allowed)}")
    if len(set(args.methods)) != len(args.methods):
        raise ValueError("Duplicate model methods are not allowed")
    cases = read_cases(args.cases)
    if args.max_cases > 0:
        cases = cases[:args.max_cases]
    if not cases:
        raise ValueError("No cases selected for evaluation")
    # Use the exact same candidate disease universe and HPO evidence snapshot
    # for knowledge baselines and supervised models.
    ml, manifest = load_verified_bundle(args.model)
    profiles = ml.profiles
    labels = ml.labels
    comparison = {}
    if args.deeprare:
        with open(args.deeprare, newline="") as f:
            comparison = {}
            for row in csv.DictReader(f):
                case_id = str(row.get("case_id", "")).strip()
                if not case_id or case_id in comparison:
                    raise ValueError(f"Empty or duplicate DeepRare case ID: {case_id!r}")
                ranks = [x.strip() for x in str(row.get("ranked_disease_ids") or "").split(";")]
                if not ranks or any(not x for x in ranks) or len(set(ranks)) != len(ranks):
                    raise ValueError(f"Invalid DeepRare ranking for case {case_id}")
                comparison[case_id] = ranks
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
            if method in ("tfidf", "logistic", "random_forest", "xgboost", "mlp"):
                if method != "tfidf" and method not in ml.models:
                    continue
                rows = ml.rank(obs, model=method, k=args.retrieval_k)
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
                            "reciprocal_rank": 1 / position if position else 0,
                            "retrieval_k": args.retrieval_k})
        if comparison:
            position = score_rank(comparison[case["case_id"]], case["disease_id"])
            records.append({"case_id": case["case_id"], "cohort": case.get("cohort", "unspecified"), "method": "DeepRare_external",
                            "true_disease_id": case["disease_id"], "known_disease": known,
                            "rank": position or "",
                            "top1": int(position == 1),
                            "top5": int(position is not None and position <= 5),
                            "reciprocal_rank": 1 / position if position else 0,
                            "retrieval_k": args.retrieval_k})
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
                            "disease_coverage": sum(r["known_disease"] for r in subset) / n,
                            "candidate_recall": sum(bool(r["rank"]) for r in subset) / n})
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
              "disease_coverage=", round(sum(r["known_disease"] for r in subset) / len(subset), 4),
              "candidate_recall=", round(sum(bool(r["rank"]) for r in subset) / len(subset), 4))
    print("Patient-level external validation only if the supplied cases are independently sourced.")


if __name__ == "__main__":
    main()
