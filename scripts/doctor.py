"""Standard-library-only environment checker for RareGenXAI.

Does not download data, train models, contact networks, or alter the machine.
Missing optional research artifacts are warnings unless explicitly required.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
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
    add("platform", "ok", f"{os_name} / {arch}; intended laptop: macOS arm64")
    in_venv = sys.prefix != sys.base_prefix
    add("virtual_environment", "ok" if in_venv else "warning",
        "Active virtual environment" if in_venv else "Run via .venv/bin/python")
    for cmd in ("git", "node", "npm"):
        add(cmd, "ok" if shutil.which(cmd) else "warning",
            "Found on PATH" if shutil.which(cmd) else
            ("Needed for phase 4 frontend" if cmd != "git" else "Install Git"))
    if minimal:
        add("dependencies", "skipped", "Skipped by --minimal for foundation CI")
    else:
        missing = [module for module in REQUIRED_MODULES
                   if importlib.util.find_spec(module) is None]
        add("dependencies", "error" if missing else "ok",
            "Missing Python modules: " + ", ".join(missing) if missing
            else "All project Python modules can be found")

    missing_data = [relative for relative in DATA_FILES if
                    not (root / relative).is_file() or
                    (root / relative).stat().st_size == 0]
    manifest_error = ""
    manifest_path = root / "data/raw/manifest.json"
    if manifest_path.is_file() and manifest_path.stat().st_size > 0:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict) or not {
                "hp.obo", "phenotype.hpoa"
            }.issubset(manifest):
                manifest_error = "manifest.json is missing HPO entries"
        except (ValueError, OSError) as exc:
            manifest_error = f"Unreadable HPO manifest: {exc}"
    data_valid = not missing_data and not manifest_error
    message = (
        "HPO ontology, annotations, manifest and profiles exist"
        if data_valid else
        "; ".join(filter(None, [
            "Missing/empty: " + ", ".join(missing_data) if missing_data else "",
            manifest_error,
            "Run: bash scripts/bootstrap_macos.sh --data",
        ]))
    )
    add("hpo_data", "ok" if data_valid else ("error" if require_data else "warning"), message)

    model_path = root / MODEL_FILE
    model_present = model_path.is_file() and model_path.stat().st_size > 0
    add("trained_model", "ok" if model_present else (
        "error" if require_model else "warning"),
        "Saved artifact exists (not inspected or trusted)" if model_present
        else "Not found; training belongs to Phase 3: python -m src.train_ml")

    available_gib = shutil.disk_usage(root).free / (1024 ** 3)
    add("free_storage", "warning" if available_gib < 10 else "ok",
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
                        help="Fail if prepared HPO data is missing")
    parser.add_argument("--require-model", action="store_true",
                        help="Fail if the saved ML model is missing")
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
