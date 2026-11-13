"""Paired bootstrap confidence intervals for external patient ranking comparisons."""
import argparse
import csv
import random
from collections import defaultdict


def summarize(rows, baseline="overlap", replicates=2000, seed=42):
    by_method = defaultdict(dict)
    for row in rows:
        by_method[row["method"]][row["case_id"]] = row
    if baseline not in by_method:
        raise ValueError("Missing baseline " + baseline)
    rng = random.Random(seed)
    result = []
    base = by_method[baseline]
    for method, cases in sorted(by_method.items()):
        common = sorted(set(base) & set(cases))
        if not common:
            continue
        for metric in ("top1", "top5", "reciprocal_rank"):
            differences = [float(cases[k][metric]) - float(base[k][metric]) for k in common]
            observed = sum(differences) / len(differences)
            draws = []
            for _ in range(replicates):
                draws.append(sum(differences[rng.randrange(len(differences))]
                                 for _ in differences) / len(differences))
            draws.sort()
            result.append({"method": method, "baseline": baseline, "metric": metric,
                           "n": len(common), "difference": round(observed, 6),
                           "ci95_low": round(draws[int(0.025 * (replicates - 1))], 6),
                           "ci95_high": round(draws[int(0.975 * (replicates - 1))], 6)})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/external_case_results.csv")
    parser.add_argument("--output", default="results/external_paired_bootstrap.csv")
    args = parser.parse_args()
    with open(args.input, newline="") as f:
        rows = list(csv.DictReader(f))
    result = summarize(rows)
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    for row in result:
        print(row)
    print("Exploratory paired case bootstrap; not a clinical efficacy claim.")


if __name__ == "__main__":
    main()
