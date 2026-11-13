"""Controlled synthetic-query benchmark. NOT external patient validation."""
import argparse
import csv
import json
import random
from pathlib import Path
from src.data import load_ontology
from src.ranking import ontology_parents, information_content, rank

def benchmark(profiles, parents, ic, labels, seed=42, trials=100, missing=0.4):
    rng = random.Random(seed)
    eligible = [d for d, terms in profiles.items() if len(terms) >= 4]
    if not eligible:
        raise ValueError("Need diseases with at least four annotated phenotypes")
    methods = [("overlap", False), ("semantic", False), ("semantic", True)]
    records = []
    for trial in range(trials):
        disease = rng.choice(eligible)
        terms = sorted(profiles[disease])
        chosen = rng.sample(terms, min(8, len(terms)))
        kept = [t for t in chosen if rng.random() >= missing]
        if not kept:
            kept = [rng.choice(chosen)]
        observations = [(t, "suspected_present" if rng.random() < 0.3 else "confirmed_present") for t in kept]
        for method, quality in methods:
            results = rank(observations, profiles, parents, ic, labels, method, quality, top_k=len(profiles))
            position = next((i for i, row in enumerate(results, 1) if row["disease_id"] == disease), None)
            records.append({"trial": trial, "disease": disease, "method": method,
                            "quality": quality, "missing_rate": missing, "rank": position,
                            "top1": int(position == 1), "top5": int(position is not None and position <= 5),
                            "reciprocal_rank": 1 / position if position else 0})
    return records

def summarize(records):
    grouped = {}
    for r in records:
        key = (r["method"], r["quality"], r["missing_rate"])
        grouped.setdefault(key, []).append(r)
    return [{"method": k[0], "quality": k[1], "missing_rate": k[2], "n": len(rows),
             "top1": sum(r["top1"] for r in rows)/len(rows),
             "top5": sum(r["top5"] for r in rows)/len(rows),
             "mrr": sum(r["reciprocal_rank"] for r in rows)/len(rows)}
            for k, rows in grouped.items()]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    data = json.loads(Path("data/processed/profiles.json").read_text())
    profiles = {k: set(v) for k, v in data["profiles"].items()}
    parents = ontology_parents(load_ontology())
    ic = information_content(profiles, parents)
    records = []
    for missing in (0.0, 0.2, 0.4, 0.6):
        records.extend(benchmark(profiles, parents, ic, data["labels"], args.seed, args.trials, missing))
    out = Path("results")
    out.mkdir(exist_ok=True)
    for filename, rows in [("synthetic_trials.csv", records), ("synthetic_summary.csv", summarize(records))]:
        with (out / filename).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print("Wrote results/synthetic_trials.csv and results/synthetic_summary.csv")
    for row in summarize(records):
        print(row)

if __name__ == "__main__":
    main()
