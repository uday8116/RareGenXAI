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
    """Download the original RareBench archive; HF dataset server cannot execute its script."""
    import io
    import zipfile
    url = "https://huggingface.co/datasets/chenxz/RareBench/resolve/main/data.zip"
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    archive_sha256 = hashlib.sha256(response.content).hexdigest()
    rows, audit = [], []
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for subset in subsets:
            matches = [name for name in archive.namelist()
                       if name.endswith(f"/{subset}.jsonl") or name == f"{subset}.jsonl"]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one JSONL file for {subset}, got {matches}")
            with archive.open(matches[0]) as handle:
                raw_cases = [json.loads(line) for line in handle]
            collected = 0
            for idx, raw in enumerate(raw_cases[:limit_per_subset]):
                terms = raw.get("Phenotype", [])
                diagnoses = raw.get("RareDisease", [])
                if isinstance(terms, str):
                    terms = re.findall(r"HP:\\d+", terms)
                if isinstance(diagnoses, str):
                    diagnoses = [diagnoses]
                if not isinstance(terms, list) or not isinstance(diagnoses, list):
                    continue
                terms = sorted({str(t) for t in terms if HPO.fullmatch(str(t))})
                diagnoses = [str(d).strip() for d in diagnoses if str(d).strip()]
                if len(terms) < 3 or len(diagnoses) != 1:
                    continue
                rows.append({"case_id": f"{subset}-{idx}",
                             "disease_id": diagnoses[0],
                             "hpo_ids": ";".join(terms), "cohort": subset})
                collected += 1
            audit.append({"subset": subset, "available": len(raw_cases),
                          "requested": min(limit_per_subset, len(raw_cases)),
                          "eligible": collected})
    return rows, audit, archive_sha256

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit-per-subset", type=int, default=30)
    p.add_argument("--subsets", nargs="+", default=["LIRICAL", "MME", "HMS"])
    p.add_argument("--output", default="data/external/rarebench_cases.csv")
    args = p.parse_args()
    rows, audit, archive_sha256 = fetch_cases(args.subsets, args.limit_per_subset)
    if not rows:
        raise RuntimeError("No usable public patient cases downloaded")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "disease_id", "hpo_ids", "cohort"])
        writer.writeheader()
        writer.writerows(rows)
    metadata = {"source": f"https://huggingface.co/datasets/{DATASET}",
                "dataset": DATASET, "archive_sha256": archive_sha256, "cohorts": audit, "eligible_total": len(rows),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "selection": "first N public test rows per cohort; >=3 valid HPO terms; single diagnosis",
                "caveat": "External patient cases, but HPO annotation knowledge overlaps candidate profiles"}
    (output.parent / "rarebench_manifest.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
