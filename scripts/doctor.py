"""Read-only local environment and HPO artifact integrity checker.

Does not download data, train models, access networks or load untrusted joblib files.
Missing optional artifacts are warnings unless explicitly required.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MODULES = (
    "numpy", "pandas", "requests", "pronto", "streamlit",
    "matplotlib", "pytest", "sklearn", "joblib", "xgboost",
)
DATA_FILES = (
    "data/raw/hp.obo",
    "data/raw/phenotype.hpoa",
    "data/raw/manifest.json",
    "data/processed/profiles.json",
)
MODEL_FILE = "models/raregen_ml.joblib"
HPO_ID = re.compile(r"^HP:\d{7}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _hpo_issues(root: Path) -> list[str]:
    """Verify local downloaded bytes and minimally validate parsed profiles."""
    missing = [relative for relative in DATA_FILES
               if not (root / relative).is_file()
               or (root / relative).stat().st_size == 0]
    if missing:
        return ["Missing/empty: " + ", ".join(missing)]
    issues: list[str] = []
    manifest_path = root / "data/raw/manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("expected JSON object")
    except (ValueError, OSError) as exc:
        return [f"Unreadable HPO manifest: {exc}"]

    for name in ("hp.obo", "phenotype.hpoa"):
        meta = manifest.get(name)
        if not isinstance(meta, dict):
            issues.append(f"manifest.json missing metadata for {name}")
            continue
        expected_sha = meta.get("sha256")
        expected_size = meta.get("bytes")
        if not isinstance(expected_sha, str) or not SHA256.fullmatch(expected_sha):
            issues.append(f"manifest.json invalid SHA-256 for {name}")
        if type(expected_size) is not int or expected_size <= 0:
            issues.append(f"manifest.json invalid size for {name}")
        path = root / "data/raw" / name
        if type(expected_size) is int and path.stat().st_size != expected_size:
            issues.append(f"{name} size differs from manifest")
        if isinstance(expected_sha, str) and SHA256.fullmatch(expected_sha):
            if _file_digest(path) != expected_sha:
                issues.append(f"{name} SHA-256 mismatch (download may be corrupted)")

    try:
        with (root / "data/raw/hp.obo").open(encoding="utf-8") as source:
            head = source.read(512)
        if "format-version:" not in head:
            issues.append("hp.obo does not have an OBO format header")
    except (OSError, UnicodeError) as exc:
        issues.append(f"hp.obo unreadable: {exc}")

    try:
        with (root / "data/raw/phenotype.hpoa").open(encoding="utf-8-sig") as source:
            header = next((line.strip() for line in source if line.strip() and
                           not line.startswith("#")), "")
        columns = set(header.split("\t"))
        if not {"database_id", "hpo_id", "qualifier"}.issubset(columns):
            issues.append("phenotype.hpoa missing required table columns")
    except (OSError, UnicodeError) as exc:
        issues.append(f"phenotype.hpoa unreadable: {exc}")

    try:
        profiles = json.loads((root / "data/processed/profiles.json").read_text(encoding="utf-8"))
        if not isinstance(profiles, dict) or not isinstance(profiles.get("profiles"), dict):
            raise ValueError("expected object with profiles mapping")
        if not isinstance(profiles.get("labels"), dict):
            raise ValueError("expected labels mapping")
        diseases = profiles["profiles"]
        if not diseases:
            raise ValueError("no disease profiles")
        for disease, terms in diseases.items():
            if not isinstance(disease, str) or not disease.strip():
                raise ValueError("empty disease identifier")
            if not isinstance(terms, list) or not all(
                isinstance(term, str) and HPO_ID.fullmatch(term) for term in terms
            ):
                raise ValueError(f"invalid HPO ID list for {disease}")
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        issues.append(f"Invalid processed profiles.json: {exc}")
    return issues


def inspect_project(
    root: Path = ROOT,
    *,
    minimal: bool = False,
    require_data: bool = False,
    require_model: bool = False,
    python_version: tuple[int, int] | None = None,
) -> dict:
    """Collect actionable checks; no modifications or network operations."""
    root = Path(root)
    checks: list[dict] = []

    def add(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    version = python_version or sys.version_info[:2]
    supported = (3, 11) <= version <= (3, 12)
    add("python", "ok" if supported else "error",
        f"{version[0]}.{version[1]} (supported: 3.11 or 3.12)")
    os_name, arch = platform.system(), platform.machine()
    platform_ok = os_name != "Darwin" or arch == "arm64"
    add("platform", "ok" if platform_ok else "error",
        f"{os_name} / {arch}" + (
            " (run Terminal natively on Apple Silicon, not under Rosetta)"
            if not platform_ok else ""
        ))
    in_venv = sys.prefix != sys.base_prefix
    add("virtual_environment", "ok" if in_venv else "warning",
        "Active virtual environment" if in_venv else "Run via .venv/bin/python")
    for cmd in ("git", "node", "npm"):
        installed = bool(shutil.which(cmd))
        add(cmd, "ok" if installed else "warning",
            "Found on PATH" if installed else
            ("Needed for later frontend phase" if cmd != "git" else "Install Git"))
    if minimal:
        add("dependencies", "skipped", "Skipped by --minimal for foundation CI")
    else:
        missing = [module for module in REQUIRED_MODULES
                   if importlib.util.find_spec(module) is None]
        add("dependencies", "error" if missing else "ok",
            "Missing Python modules: " + ", ".join(missing) if missing
            else "All project Python modules can be found")

    issues = _hpo_issues(root)
    add("hpo_data", ("error" if require_data else "warning") if issues else "ok",
        "; ".join(issues) + ("; run bash scripts/bootstrap_macos.sh --data"
                             if issues else "") if issues else
        "HPO ontology/annotations verified against manifest; profiles parsed")

    model_path = root / MODEL_FILE
    model_present = model_path.is_file() and model_path.stat().st_size > 0
    add("trained_model", "ok" if model_present else (
        "error" if require_model else "warning"),
        "Saved artifact exists (not loaded, verified or trusted)" if model_present
        else "Not found; training belongs to Phase 3: python -m src.train_ml")

    available_gib = shutil.disk_usage(root).free / (1024 ** 3)
    add("free_storage", "warning" if available_gib < 25 else "ok",
        f"{available_gib:.1f} GiB available; 25+ GiB recommended")
    return {
        "ok": not any(item["status"] == "error" for item in checks),
        "checks": checks,
        "project_root": str(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimal", action="store_true",
                        help="Skip dependency checks (CI or before setup)")
    parser.add_argument("--require-data", action="store_true",
                        help="Fail if prepared HPO data is missing or corrupted")
    parser.add_argument("--require-model", action="store_true",
                        help="Fail if a saved ML file is missing; does not load it")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    report = inspect_project(
        minimal=args.minimal, require_data=args.require_data,
        require_model=args.require_model,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("RareGenXAI environment doctor")
        for item in report["checks"]:
            print(f"[{item['status'].upper()}] {item['name']}: {item['detail']}")
        print("READY" if report["ok"] else "ACTION REQUIRED")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
