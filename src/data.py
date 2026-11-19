"""Download and parse official HPO ontology and disease annotations."""
from pathlib import Path
import hashlib
import os
import time
import uuid
import json
import requests
import pandas as pd
import pronto

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
URLS = {
    "hp.obo": "https://purl.obolibrary.org/obo/hp.obo",
    "phenotype.hpoa": "https://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa",
}

def download(force=False):
    """Download official HPO data with retry and atomic output files.

    Failed/interrupted network transfers never replace an existing good file,
    and temporary partial files are cleaned up. Retrying transient HTTP and
    network errors helps when the official PURLs disconnect under CI load.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, url in URLS.items():
        target = RAW / name
        if force or not target.exists():
            temp = RAW / f".{name}.{uuid.uuid4().hex}.partial"
            last_error = None
            try:
                for attempt in range(4):
                    try:
                        with requests.get(url, stream=True, timeout=120) as response:
                            response.raise_for_status()
                            with temp.open("wb") as out:
                                for chunk in response.iter_content(1024 * 1024):
                                    if chunk:
                                        out.write(chunk)
                        if temp.stat().st_size < 1000:
                            raise ValueError(f"Unexpectedly small download: {temp}")
                        os.replace(temp, target)
                        last_error = None
                        break
                    except requests.RequestException as exc:
                        last_error = exc
                        temp.unlink(missing_ok=True)
                        if attempt < 3:
                            time.sleep(2 ** attempt)
                if last_error is not None:
                    raise RuntimeError(f"Could not download official HPO {name} after four attempts") from last_error
            finally:
                temp.unlink(missing_ok=True)
        if target.stat().st_size < 1000:
            raise ValueError(f"Unexpectedly small download: {target}")
        manifest[name] = {
            "url": url,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "bytes": target.stat().st_size,
        }
    manifest_path = RAW / "manifest.json"
    temp_manifest = RAW / f".manifest.{uuid.uuid4().hex}.partial"
    try:
        temp_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        os.replace(temp_manifest, manifest_path)
    finally:
        temp_manifest.unlink(missing_ok=True)
    return manifest

def load_annotations(path=RAW / "phenotype.hpoa"):
    """HPOA is tab-separated; lines starting # are metadata."""
    df = pd.read_csv(path, sep="\t", comment="#", dtype=str, keep_default_na=False)
    required = {"database_id", "hpo_id", "qualifier"}
    if not required.issubset(df.columns):
        raise ValueError(f"Unexpected HPOA schema: {list(df.columns)}. Expected {required}")
    df = df[df["hpo_id"].str.startswith("HP:")].copy()
    return df

def build_profiles(df):
    """Only positive disease annotations; NOT qualifiers are kept separate."""
    profiles, negatives, labels = {}, {}, {}
    for row in df.to_dict("records"):
        disease, hp = row["database_id"], row["hpo_id"]
        labels[disease] = row.get("disease_name", disease) or disease
        target = negatives if "NOT" in row.get("qualifier", "").upper() else profiles
        target.setdefault(disease, set()).add(hp)
    return profiles, negatives, labels

def prepare():
    download()
    df = load_annotations()
    profiles, negatives, labels = build_profiles(df)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    payload = {
        "profiles": {k: sorted(v) for k, v in profiles.items()},
        "negatives": {k: sorted(v) for k, v in negatives.items()},
        "labels": labels,
    }
    (PROCESSED / "profiles.json").write_text(json.dumps(payload))
    print(f"Prepared {len(profiles)} disease profiles from {len(df)} annotations")
    return payload

def load_ontology(path=RAW / "hp.obo"):
    return pronto.Ontology(str(path))

if __name__ == "__main__":
    prepare()
