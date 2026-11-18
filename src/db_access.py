"""Parameterized read-only access for HPO terms and rare-disease knowledge.

This module is intended for future FastAPI and model-ranking integrations.
Only public research knowledge is persisted; no patient records are accepted.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import quote

DEFAULT_DB = Path("data/local/raregen.sqlite3")


def connect_readonly(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Local knowledge database missing: {path}. Run: python -m src.knowledge_db build")
    uri = f"file:{quote(str(path), safe='/')}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _limit(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > 100:
        raise ValueError("limit must be an integer between 1 and 100")
    return value


def _pattern(value: str) -> str:
    return value.replace("!", "!!").replace("%", "!%").replace("_", "!_")


def phenotype(conn: sqlite3.Connection, hpo_id: str) -> dict | None:
    row = conn.execute(
        """SELECT h.hpo_id,h.name,h.definition,h.is_obsolete
           FROM hpo_terms h WHERE h.hpo_id=?
           UNION ALL
           SELECT h.hpo_id,h.name,h.definition,h.is_obsolete
           FROM hpo_aliases a JOIN hpo_terms h ON h.hpo_id=a.hpo_id
           WHERE a.alias_id=?
           LIMIT 1""", (hpo_id, hpo_id)
    ).fetchone()
    return dict(row) if row else None


def search_phenotypes(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    """Find exact IDs and common name prefixes first; then name/synonym matches."""
    limit = _limit(limit)
    query = query.strip()
    if not query:
        return []
    q = _pattern(query)
    prefix = f"{q}%"
    contains = f"%{q}%"
    sql = """SELECT h.hpo_id,h.name,h.is_obsolete FROM hpo_terms h
        WHERE h.hpo_id LIKE ? ESCAPE '!'
           OR h.name LIKE ? ESCAPE '!' COLLATE NOCASE
           OR EXISTS (SELECT 1 FROM hpo_aliases a WHERE a.hpo_id=h.hpo_id
                      AND a.alias_id LIKE ? ESCAPE '!')
           OR EXISTS (SELECT 1 FROM hpo_synonyms s WHERE s.hpo_id=h.hpo_id
                      AND s.synonym LIKE ? ESCAPE '!' COLLATE NOCASE)
        ORDER BY h.is_obsolete, CASE WHEN h.hpo_id=? THEN 0
                                    WHEN lower(h.name)=lower(?) THEN 1
                                    ELSE 2 END,
                 h.name COLLATE NOCASE, h.hpo_id LIMIT ?"""
    rows = conn.execute(sql, (prefix, prefix, prefix, prefix, query, query, limit)).fetchall()
    found = {r["hpo_id"]: dict(r) for r in rows}
    if len(found) < limit:
        remaining = limit - len(found)
        extras = conn.execute(
            """SELECT h.hpo_id,h.name,h.is_obsolete FROM hpo_terms h
               WHERE h.name LIKE ? ESCAPE '!' COLLATE NOCASE
                  OR EXISTS (SELECT 1 FROM hpo_synonyms s WHERE s.hpo_id=h.hpo_id
                             AND s.synonym LIKE ? ESCAPE '!' COLLATE NOCASE)
               ORDER BY h.is_obsolete,h.name COLLATE NOCASE,h.hpo_id LIMIT ?""",
            (contains, contains, limit + len(found)),
        ).fetchall()
        for row in extras:
            if row["hpo_id"] not in found and remaining:
                found[row["hpo_id"]] = dict(row)
                remaining -= 1
    return list(found.values())


def search_diseases(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    limit = _limit(limit)
    query = query.strip()
    if not query:
        return []
    q = _pattern(query)
    rows = conn.execute(
        """SELECT disease_id,name FROM diseases
           WHERE disease_id LIKE ? ESCAPE '!' OR name LIKE ? ESCAPE '!' COLLATE NOCASE
           ORDER BY CASE WHEN disease_id=? THEN 0 ELSE 1 END,name COLLATE NOCASE,disease_id
           LIMIT ?""", (f"{q}%", f"%{q}%", query, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def disease_detail(conn: sqlite3.Connection, disease_id: str) -> dict | None:
    disease = conn.execute(
        "SELECT disease_id,name FROM diseases WHERE disease_id=?", (disease_id,)
    ).fetchone()
    if disease is None:
        return None
    annotations = conn.execute(
        """SELECT p.hpo_id,t.name AS hpo_name,p.is_negated,p.frequency,p.evidence_code,
                  p.reference_id,p.onset,p.sex,p.aspect
           FROM disease_phenotypes p JOIN hpo_terms t ON p.hpo_id=t.hpo_id
           WHERE p.disease_id=? ORDER BY p.is_negated,p.hpo_id,p.annotation_id""",
        (disease_id,),
    ).fetchall()
    return {**dict(disease), "phenotypes": [dict(row) for row in annotations]}


def load_ranking_inputs(conn: sqlite3.Connection) -> tuple[dict, dict, dict, dict]:
    """Return profiles, explicitly negated profiles, labels and parent IDs.

    These shapes are compatible with the existing phenotype ranking code.
    Multiple evidence records for the same disease/phenotype collapse to a set.
    """
    profiles: dict[str, set[str]] = {}
    negatives: dict[str, set[str]] = {}
    labels: dict[str, str] = {}
    parents: dict[str, set[str]] = {}
    for r in conn.execute("SELECT disease_id,name FROM diseases"):
        labels[r["disease_id"]] = r["name"]
    for r in conn.execute("SELECT disease_id,hpo_id,is_negated FROM disease_phenotypes"):
        target = negatives if r["is_negated"] else profiles
        target.setdefault(r["disease_id"], set()).add(r["hpo_id"])
    for r in conn.execute("SELECT child_id,parent_id FROM hpo_parents"):
        parents.setdefault(r["child_id"], set()).add(r["parent_id"])
    return profiles, negatives, labels, parents


def stats(conn: sqlite3.Connection) -> dict:
    tables = ("hpo_terms", "hpo_aliases", "hpo_synonyms", "hpo_parents",
              "diseases", "disease_phenotypes")
    counts = {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
              for name in tables}
    counts["negative_annotations"] = conn.execute(
        "SELECT COUNT(*) FROM disease_phenotypes WHERE is_negated=1"
    ).fetchone()[0]
    metadata = {r["key"]: r["value"] for r in conn.execute("SELECT key,value FROM db_metadata")}
    sources = [dict(row) for row in conn.execute(
        "SELECT filename,source_url,sha256,byte_count FROM data_sources ORDER BY filename"
    )]
    return {"counts": counts, "metadata": metadata, "sources": sources}
