"""Build and verify a reproducible local HPO/rare-disease SQLite knowledge base.

Usage:
  python -m src.knowledge_db build [--replace]
  python -m src.knowledge_db verify
  python -m src.knowledge_db search-hpo "seizure"
  python -m src.knowledge_db search-disease "Marfan"

Reads official HPO files prepared by python -m src.data. Never stores patient data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from src.data import load_ontology
from src.db_access import DEFAULT_DB, connect_readonly, disease_detail
from src.db_access import search_diseases, search_phenotypes, stats
from src.db_schema import SCHEMA_VERSION, apply_migrations

DEFAULT_RAW = Path("data/raw")
HPO_RE = re.compile(r"^HP:\d{7}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_sources(raw_dir: Path) -> dict:
    """Require byte-perfect official downloads recorded in the Phase 1 manifest."""
    manifest = json.loads((raw_dir / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("HPO manifest must be a JSON object")
    for filename in ("hp.obo", "phenotype.hpoa"):
        metadata = manifest.get(filename)
        if not isinstance(metadata, dict):
            raise ValueError(f"Missing source manifest entry for {filename}")
        sha = metadata.get("sha256")
        size = metadata.get("bytes")
        url = metadata.get("url")
        if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
            raise ValueError(f"Invalid SHA-256 for {filename}")
        if type(size) is not int or size < 1 or not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError(f"Invalid source metadata for {filename}")
        path = raw_dir / filename
        if path.stat().st_size != size or checksum(path) != sha:
            raise ValueError(f"Source checksum/length mismatch for {filename}; redownload official HPO")
    return manifest


def validate_connection(conn: sqlite3.Connection, raw_dir: Path | None = None) -> dict:
    """Check SQLite integrity, full annotation accounting, and source provenance."""
    conn.row_factory = sqlite3.Row
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"Unexpected DB schema version: {version} (expected {SCHEMA_VERSION}). "
            "Rebuild with: python -m src.knowledge_db build --replace"
        )
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("SQLite integrity_check failed")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("SQLite foreign key checks failed")
    result = stats(conn)
    counts = result["counts"]
    if not counts["hpo_terms"] or not counts["diseases"] or not counts["disease_phenotypes"]:
        raise ValueError("Knowledge database has no terms, diseases, or annotations")
    sources = {row["filename"]: row for row in result["sources"]}
    if set(sources) != {"hp.obo", "phenotype.hpoa"}:
        raise ValueError("Missing or unexpected source provenance entries")
    for name, data in sources.items():
        if not SHA_RE.fullmatch(data["sha256"]) or data["byte_count"] <= 0:
            raise ValueError(f"Invalid recorded provenance for {name}")
    metadata = result["metadata"]
    try:
        read = int(metadata["annotation_rows_read"])
        duplicates = int(metadata["duplicate_annotations"])
        unmapped = int(metadata["unmapped_annotations"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"Missing/invalid annotation accounting: {exc}") from exc
    if (read != counts["hpoa_source_rows"] or
            duplicates != read - counts["disease_phenotypes"] or
            unmapped != 0 or read < 1):
        raise ValueError(
            "Annotation accounting mismatch: source rows, compact associations "
            "and duplicate counts must agree"
        )
    if raw_dir is not None:
        manifest = verify_sources(Path(raw_dir))
        for name in ("hp.obo", "phenotype.hpoa"):
            data = sources[name]
            if (data["source_url"] != manifest[name]["url"] or
                    data["sha256"] != manifest[name]["sha256"] or
                    data["byte_count"] != manifest[name]["bytes"]):
                raise ValueError(f"Database provenance differs from local {name}")
    return result


def _annotations(path: Path):
    """Strict streaming HPOA parser: never silently drop malformed HPO IDs."""
    columns = (
        "database_id", "disease_name", "qualifier", "hpo_id", "reference",
        "evidence", "onset", "frequency", "sex", "modifier", "aspect",
        "biocuration",
    )
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(
            (line for line in handle if not line.lstrip().startswith("#")),
            delimiter="\t", restkey="__unexpected_columns__", restval=None,
        )
        if not reader.fieldnames or set(reader.fieldnames) != set(columns):
            raise ValueError(
                f"HPOA format drift: expected 12 named columns {columns}, "
                f"got {reader.fieldnames}"
            )
        for index, row in enumerate(reader, start=1):
            if "__unexpected_columns__" in row or any(row.get(name) is None for name in columns):
                raise ValueError(f"HPOA row {index} has incorrect column count")
            yield index, {name: str(row[name]).strip() for name in columns}


def _populate(conn: sqlite3.Connection, raw_dir: Path, manifest: dict) -> dict:
    ontology = load_ontology(raw_dir / "hp.obo")
    terms = [term for term in ontology.terms() if HPO_RE.fullmatch(term.id)]
    ids = {term.id for term in terms}
    if not ids:
        raise ValueError("No HPO terms found in ontology")

    for term in terms:
        conn.execute(
            "INSERT INTO hpo_terms(hpo_id,name,definition,is_obsolete) VALUES (?,?,?,?)",
            (term.id, term.name or term.id, str(term.definition or ""), int(term.obsolete)),
        )
    aliases: dict[str, str] = {}
    for term in terms:
        for alt in term.alternate_ids:
            if HPO_RE.fullmatch(alt) and alt != term.id and alt not in ids:
                if alt in aliases and aliases[alt] != term.id:
                    raise ValueError(f"Ambiguous HPO alternate ID: {alt}")
                aliases[alt] = term.id
        for synonym in term.synonyms:
            value = synonym.description.strip()
            if value:
                conn.execute(
                    "INSERT OR IGNORE INTO hpo_synonyms(hpo_id,synonym) VALUES (?,?)",
                    (term.id, value),
                )
        for parent in term.superclasses(distance=1, with_self=False):
            if parent.id in ids and parent.id != term.id:
                conn.execute(
                    "INSERT OR IGNORE INTO hpo_parents(child_id,parent_id) VALUES (?,?)",
                    (term.id, parent.id),
                )
    conn.executemany("INSERT INTO hpo_aliases(alias_id,hpo_id) VALUES (?,?)",
                     sorted(aliases.items()))
    seen = 0
    for seen, row in _annotations(raw_dir / "phenotype.hpoa"):
        disease_id, raw_id = row["database_id"], row["hpo_id"]
        qualifier = row["qualifier"].upper()
        aspect = row["aspect"].upper()
        if not disease_id or ":" not in disease_id or not row["disease_name"]:
            raise ValueError(f"Malformed disease ID/name in HPOA row {seen}")
        if not HPO_RE.fullmatch(raw_id):
            raise ValueError(f"Invalid HPO ID {raw_id!r} in HPOA row {seen}")
        if qualifier not in ("", "NOT"):
            raise ValueError(f"Unknown HPOA qualifier {qualifier!r} in row {seen}")
        if aspect not in {"P", "C", "I", "M", "H"}:
            raise ValueError(f"Unexpected HPOA aspect {aspect!r} in row {seen}")
        if not row["reference"] or not row["evidence"] or not row["biocuration"]:
            raise ValueError(f"Missing mandatory HPOA evidence/reference/biocuration in row {seen}")
        hp = raw_id if raw_id in ids else aliases.get(raw_id)
        if hp is None:
            raise ValueError(f"Unknown HPO term {raw_id!r} in HPOA row {seen}")
        name = row["disease_name"]
        conn.execute("INSERT OR IGNORE INTO diseases(disease_id,name) VALUES (?,?)",
                     (disease_id, name))
        conn.execute(
            """INSERT INTO hpoa_source_rows(
                   row_number,disease_id,disease_name,raw_hpo_id,hpo_id,
                   qualifier,reference_id,evidence_code,onset,frequency,sex,
                   modifier,aspect,biocuration)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (seen, disease_id, name, raw_id, hp, qualifier, row["reference"],
             row["evidence"], row["onset"], row["frequency"], row["sex"],
             row["modifier"], aspect, row["biocuration"]),
        )
        conn.execute(
            """INSERT OR IGNORE INTO disease_phenotypes(
                 disease_id,hpo_id,is_negated,evidence_code,reference_id,
                 frequency,onset,sex,modifier,aspect,biocuration)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (disease_id, hp, int(qualifier == "NOT"), row["evidence"],
             row["reference"], row["frequency"], row["onset"], row["sex"],
             row["modifier"], aspect, row["biocuration"]),
        )
    if seen == 0:
        raise ValueError("No HPOA annotation rows found")
    compact_count = conn.execute("SELECT COUNT(*) FROM disease_phenotypes").fetchone()[0]

    for filename in ("hp.obo", "phenotype.hpoa"):
        data = manifest[filename]
        conn.execute(
            "INSERT INTO data_sources(filename,source_url,sha256,byte_count) VALUES (?,?,?,?)",
            (filename, data["url"], data["sha256"], data["bytes"]),
        )
    metadata = {
        "schema_version": str(SCHEMA_VERSION),
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "annotation_rows_read": str(seen),
        "unmapped_annotations": "0",
        "duplicate_annotations": str(seen - compact_count),
        "annotation_source_type": "public_HPO_disease_knowledge_not_patient_records",
    }
    conn.executemany("INSERT INTO db_metadata(key,value) VALUES (?,?)", metadata.items())
    return metadata


def build_database(raw_dir: str | Path = DEFAULT_RAW, db_path: str | Path = DEFAULT_DB,
                   *, replace: bool = False) -> dict:
    """Build in a temporary SQLite file; only replace destination after validation."""
    raw_dir, destination = Path(raw_dir), Path(db_path)
    manifest = verify_sources(raw_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not replace:
        raise FileExistsError(f"{destination} exists; pass --replace for deliberate rebuild")
    staging = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    conn = None
    try:
        conn = sqlite3.connect(staging)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        apply_migrations(conn)
        with conn:
            _populate(conn, raw_dir, manifest)
        if verify_sources(raw_dir) != manifest:
            raise ValueError("HPO files or manifest changed during database import")
        result = validate_connection(conn, raw_dir=raw_dir)
        conn.close()
        conn = None
        if destination.exists() and not replace:
            raise FileExistsError(f"{destination} appeared during build; aborting")
        os.replace(staging, destination)
        return result
    finally:
        if conn is not None:
            conn.close()
        staging.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Import official local files into SQLite")
    build.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    build.add_argument("--db", type=Path, default=DEFAULT_DB)
    build.add_argument("--replace", action="store_true",
                       help="Replace existing database only after a successful validated import")
    for command in ("verify", "stats", "search-hpo", "search-disease", "disease"):
        p = sub.add_parser(command)
        p.add_argument("--db", type=Path, default=DEFAULT_DB)
        if command == "verify":
            p.add_argument("--raw-dir", type=Path, default=None,
                           help="Compare DB source hashes with local HPO files")
        if command.startswith("search"):
            p.add_argument("query")
            p.add_argument("--limit", type=int, default=20)
        if command == "disease":
            p.add_argument("disease_id")
    args = parser.parse_args(argv)
    if args.command == "build":
        output = build_database(args.raw_dir, args.db, replace=args.replace)
    else:
        with closing(connect_readonly(args.db)) as conn:
            if args.command == "verify":
                output = validate_connection(conn, raw_dir=args.raw_dir)
            elif args.command == "stats":
                output = stats(conn)
            elif args.command == "search-hpo":
                output = search_phenotypes(conn, args.query, args.limit)
            elif args.command == "search-disease":
                output = search_diseases(conn, args.query, args.limit)
            else:
                output = disease_detail(conn, args.disease_id)
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
