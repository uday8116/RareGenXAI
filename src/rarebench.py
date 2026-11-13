"""Fetch independent, published RareBench patient cases from Hugging Face.

This is an external case benchmark, NOT an independent HPO knowledge base:
disease annotations still overlap the knowledge used by the rankers.
Sources: https://huggingface.co/datasets/chenxz/RareBench
The API returns de-identified HPO observations and disease identifiers.
"""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
import requests

API = "https://datasets-server.huggingface.co"
DATASET = "chenxz/RareBench"
HPO = re.compile(r"^HP:\d+$")


def fetch_cases(subsets=("LIRICAL", "MME", "HMS"), limit_per_subset=30):
    session = requests.Session()
    response = session.get(f"{API}/splits", params={"dataset": DATASET}, timeout=90)
    response.raise_for_status()
    splits = response.json()["splits"]
    rows, audit = [], []
    for subset in subsets:
        options = [s for s in splits if s["config"].lower() == subset.lower() and s["split"] == "test"]
        if not options:
            raise ValueError(f"No public test split for {subset}; available: {[(s['config'],s['split']) for s in splits]}")
        item = options[0]
        total = min(int(item["num_rows"]), limit_per_subset)
        collected = 0
        for offset in range(0, total, 100):
            request = session.get(f"{API}/rows", params={"dataset": DATASET,
                "config": item["config"], "split": item["split"], "offset": offset,
                "length": min(100, total-offset)}, timeout=120)
            request.raise_for_status()
            for entry in request.json()["rows"]:
                raw = entry["row"]
                terms = raw.get("Phenotype", [])
                diagnoses = raw.get("RareDisease", [])
                if isinstance(terms, str):
                    try:
                        terms = json.loads(terms)
                    except json.JSONDecodeError:
                        terms = re.findall(r"HP:\d+", terms)
                if isinstance(diagnoses, str):
                    try:
                        diagnoses = json.loads(diagnoses)
                    except json.JSONDecodeError:
                        diagnoses = [diagnoses]
                if not isinstance(terms, list) or not isinstance(diagnoses, list):
                    continue
                terms = sorted({str(t) for t in terms if HPO.fullmatch(str(t))})
                diagnoses = [str(d) for d in diagnoses if str(d).strip()]
                if len(terms) < 3 or len(diagnoses) != 1:
                    continue
                rows.append({"case_id": f"{subset}-{entry['row_idx']}",
                             "disease_id": diagnoses[0],
                             "hpo_ids": ";".join(terms), "cohort": subset})
                collected += 1
        audit.append({"subset": subset, "available": item["num_rows"], "requested": total,
                      "eligible": collected})
    return rows, audit


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit-per-subset", type=int, default=30)
    p.add_argument("--subsets", nargs="+", default=["LIRICAL", "MME", "HMS"])
    p.add_argument("--output", default="data/external/rarebench_cases.csv")
    args = p.parse_args()
    rows, audit = fetch_cases(args.subsets, args.limit_per_subset)
    if not rows:
        raise RuntimeError("No usable public patient cases downloaded")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "disease_id", "hpo_ids", "cohort"])
        writer.writeheader()
        writer.writerows(rows)
    metadata = {"source": f"https://huggingface.co/datasets/{DATASET}",
                "dataset": DATASET, "cohorts": audit, "eligible_total": len(rows),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "selection": "first N public test rows per cohort; >=3 valid HPO terms; single diagnosis",
                "caveat": "External patient cases, but HPO annotation knowledge overlaps candidate profiles"}
    (output.parent / "rarebench_manifest.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
