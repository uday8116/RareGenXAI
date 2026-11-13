"""Controlled evidence-weight sensitivity analysis on small, deterministic toy cases.

This does NOT claim independent clinical validation. It tests whether the proposed
scoring design behaves sensibly when an observation is uncertain or absent.
"""
import csv
from pathlib import Path
from src.ranking import rank

def main():
    profiles = {
        "A": {"HP:0000001", "HP:0000002"},
        "B": {"HP:0000001", "HP:0000003"},
    }
    parents = {t: set() for terms in profiles.values() for t in terms}
    ic = {t: 1.0 for t in parents}
    cases = [
        ("confirmed_positive", [("HP:0000002", "confirmed_present")]),
        ("suspected_positive", [("HP:0000002", "suspected_present")]),
        ("contradictory_negative", [("HP:0000001", "confirmed_present"), ("HP:0000002", "confirmed_absent")]),
        ("unknown_ignored", [("HP:0000002", "confirmed_present"), ("HP:0000003", "unknown")]),
    ]
    rows = []
    for name, observations in cases:
        for quality in (False, True):
            results = rank(observations, profiles, parents, ic, method="overlap", quality=quality, top_k=2)
            for item in results:
                rows.append({"case": name, "evidence_weighting": quality,
                             "disease": item["disease_id"], "score": item["score"],
                             "rank": results.index(item) + 1})
    out = Path("results")
    out.mkdir(exist_ok=True)
    with (out / "evidence_behavior.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("Wrote results/evidence_behavior.csv (controlled toy experiment, NOT clinical validation)")

if __name__ == "__main__":
    main()
