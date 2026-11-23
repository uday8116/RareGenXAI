"""Phase 10: deliberately local, integrity-checked research artifact backups.

Default backup includes only a fixed allowlist of local research files and
NEVER serializes arbitrary folder contents, credentials, or patient records.
Restore only into a new, empty destination. Does not load joblib models.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
import zipfile

SCHEMA = "raregen_phase10_research_backup_v1"
MANIFEST = "backup_manifest.json"

CORE_FILES = (
    "data/raw/hp.obo",
    "data/raw/phenotype.hpoa",
    "data/raw/manifest.json",
    "data/local/raregen.sqlite3",
    "models/raregen_ml.joblib",
    "models/raregen_ml.manifest.json",
)
# Exclude patient-case data and all unscreened directory contents by default.
OPTIONAL_FILES = (
    "data/external/rarebench_cases.csv",
    "data/external/rarebench_manifest.json",
    "results/phase7_plan.json",
    "results/phase7_provenance.json",
    "results/phase7_research_report.md",
    "results/phase7_case_audit.csv",
    "results/phase7_cohort_metrics.csv",
    "results/phase7_paired_effects.csv",
    "results/phase7_error_analysis.csv",
    "results/external_case_results.csv",
    "results/external_cohort_summary.csv",
)
ALL_ALLOWED = frozenset(CORE_FILES + OPTIONAL_FILES)
MAX_FILE_BYTES = 2 * 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 6 * 1024 * 1024 * 1024


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def safe_member(name):
    if not isinstance(name, str) or name not in ALL_ALLOWED:
        raise ValueError(f"Unapproved backup member: {name!r}")
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or "\\" in name or name.startswith("/"):
        raise ValueError(f"Unsafe path: {name!r}")
    return p


def _ensure_local_regular(path, root):
    """Never traverse an attacker-controlled symlink in source paths."""
    root = Path(root).resolve(strict=True)
    relative = path.relative_to(root)
    current = root
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise ValueError(f"Backup symlink forbidden: {relative}")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"Not a regular file: {relative}")
    if info.st_size > MAX_FILE_BYTES:
        raise ValueError(f"Artifact exceeds file size limit: {relative}")
    return info.st_size


def create(root, target, include_cases=False):
    root = Path(root).resolve(strict=True)
    target = Path(target).absolute()
    if target.exists():
        raise FileExistsError(f"Backup destination already exists: {target}")
    if target.parent.is_symlink():
        raise ValueError("Backup destination parent must not be a symlink")
    target.parent.mkdir(parents=True, exist_ok=True)
    included = CORE_FILES + (OPTIONAL_FILES if include_cases else ())
    manifest = {"schema": SCHEMA, "research_only": True,
                "case_results_opt_in": bool(include_cases), "files": {}}
    sources = []
    total = 0
    for name in included:
        path = root / name
        if not path.exists() and not path.is_symlink():
            continue
        size = _ensure_local_regular(path, root)
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Backup exceeds maximum total size")
        manifest["files"][name] = {"sha256": digest(path), "bytes": size}
        sources.append((name, path))
    if not sources:
        raise ValueError("No approved research artifacts found; prepare HPO/model files first")
    # Backup is for recovery. Missing expected artifacts are visible as a
    # completeness warning, never silently inferred to exist.
    manifest["missing_core"] = [name for name in CORE_FILES if name not in manifest["files"]]
    fd, temp_name = tempfile.mkstemp(prefix=".phase10-", suffix=".zip", dir=target.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            for name, path in sources:
                archive.write(path, arcname=name)
            archive.writestr(MANIFEST, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        verify(temp_name)
        # Fail rather than clobber an existing backup created during packaging.
        with open(temp_name, "rb") as src, target.open("xb") as dst:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(chunk)
    except Exception:
        if target.exists():
            target.unlink()
        raise
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return manifest


def _validated_archive(archive):
    names = archive.namelist()
    if len(names) != len(set(names)) or MANIFEST not in names:
        raise ValueError("Missing manifest or duplicate archive member")
    if len(names) > len(ALL_ALLOWED) + 1:
        raise ValueError("Unexpected archive member count")
    for entry in archive.infolist():
        if entry.filename != MANIFEST:
            safe_member(entry.filename)
        if entry.is_dir():
            raise ValueError("Directories not permitted in backup archive")
        if (entry.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
            raise ValueError("Symlinks not permitted in backup archive")
        if entry.file_size > MAX_FILE_BYTES:
            raise ValueError("Archive member too large")
    if archive.getinfo(MANIFEST).file_size > 64 * 1024:
        raise ValueError("Manifest exceeds size limit")
    manifest = json.loads(archive.read(MANIFEST))
    if manifest.get("schema") != SCHEMA or manifest.get("research_only") is not True:
        raise ValueError("Unsupported research backup format")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files or set(files) != set(names) - {MANIFEST}:
        raise ValueError("Manifest members differ from ZIP entries")
    opt_in = manifest.get("case_results_opt_in")
    if type(opt_in) is not bool:
        raise ValueError("Missing opt-in flag")
    if not opt_in and any(name in OPTIONAL_FILES for name in files):
        raise ValueError("Optional case or result files without explicit opt-in")
    missing = manifest.get("missing_core")
    if not isinstance(missing, list) or missing != [x for x in CORE_FILES if x not in files]:
        raise ValueError("Invalid core-file completeness record")
    for name, record in files.items():
        safe_member(name)
        if (not isinstance(record, dict) or
                type(record.get("bytes")) is not int or record["bytes"] < 0 or
                record["bytes"] > MAX_FILE_BYTES or
                not isinstance(record.get("sha256"), str) or
                len(record["sha256"]) != 64 or
                any(c not in "0123456789abcdef" for c in record["sha256"])):
            raise ValueError(f"Invalid manifest record: {name}")
        if archive.getinfo(name).file_size != record["bytes"]:
            raise ValueError(f"Manifest size mismatch: {name}")
    if sum(v["bytes"] for v in files.values()) > MAX_TOTAL_BYTES:
        raise ValueError("Total backup size exceeded")
    return manifest


def verify(path):
    with zipfile.ZipFile(path, "r") as archive:
        manifest = _validated_archive(archive)
        for name, record in manifest["files"].items():
            sha = hashlib.sha256()
            count = 0
            with archive.open(name, "r") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    count += len(chunk)
                    if count > record["bytes"]:
                        raise ValueError(f"Unexpected uncompressed size: {name}")
                    sha.update(chunk)
            if sha.hexdigest() != record["sha256"] or count != record["bytes"]:
                raise ValueError(f"SHA-256 mismatch: {name}")
        return manifest


def restore(path, destination):
    # Verify every member before making changes to the target.
    manifest = verify(path)
    dest = Path(destination).absolute()
    if dest.is_symlink() or (dest.exists() and (not dest.is_dir() or any(dest.iterdir()))):
        raise FileExistsError("Restore target must be a new or empty non-symlink directory")
    if dest.parent.is_symlink():
        raise ValueError("Restore parent must not be a symlink")
    dest.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(path, "r") as archive:
            for name in manifest["files"]:
                relative = safe_member(name)
                output = dest.joinpath(*relative.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, output.open("xb") as target:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        target.write(chunk)
                if digest(output) != manifest["files"][name]["sha256"]:
                    raise ValueError(f"Post-restore verification failed for {name}")
    except Exception:
        # Never silently claim a partial restore is complete. User can delete
        # the target directory manually if a disk error interrupted extraction.
        raise
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="RareGenXAI local research backup")
    commands = parser.add_subparsers(dest="command", required=True)
    a = commands.add_parser("create", help="Back up allowed local artifacts")
    a.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    a.add_argument("--out", type=Path, required=True)
    a.add_argument("--include-case-results", action="store_true",
                   help="Explicitly opt in to potentially sensitive archived cases/results")
    b = commands.add_parser("verify", help="Verify all archive members against SHA-256")
    b.add_argument("--archive", type=Path, required=True)
    c = commands.add_parser("restore", help="Restore ONLY to a new/empty folder")
    c.add_argument("--archive", type=Path, required=True)
    c.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = create(args.root, args.out, args.include_case_results)
        elif args.command == "verify":
            result = verify(args.archive)
        else:
            result = restore(args.archive, args.destination)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS {args.command}: {len(result['files'])} verified local research files")
    if result["missing_core"]:
        print("WARNING: missing core artifacts:", ", ".join(result["missing_core"]))
    if result["case_results_opt_in"]:
        print("WARNING: case/results included. Review access, licensing and sharing.")
    print("No joblib artifact was deserialized. Research only; not clinical validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
