"""Parameterized read-only access for HPO terms and rare-disease knowledge.

This module is intended for future FastAPI and model-ranking integrations.
Only public research knowledge is persisted; no patient records are accepted.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
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


@contextmanager
def open_readonly(db_path: str | Path = DEFAULT_DB):
    """Read-only connection that is always closed at context exit."""
    connection = connect_readonly(db_path)
    try:
        yield connection
    finally:
        connection.close()


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
    """Return canonical HPO IDs ranked by exact ID/alias/name/synonym then prefix.

    Uses indexed lookups where possible; all input remains bound SQL parameters.
    Exact synonym matches are not hidden behind alphabetically earlier prefixes.
    """
    limit = _limit(limit)
    if not isinstance(query, str):
        raise ValueError("query must be text")
    query = query.strip()
    if not query:
        return []
    q = _pattern(query)
    prefix, contains = f"{q}%", f"%{q}%"
    sql = """WITH matches AS (
          SELECT hpo_id,0 AS priority FROM hpo_terms WHERE hpo_id=?
          UNION ALL SELECT hpo_id,1 FROM hpo_aliases WHERE alias_id=?
          UNION ALL SELECT hpo_id,2 FROM hpo_terms WHERE name=? COLLATE NOCASE
          UNION ALL SELECT hpo_id,3 FROM hpo_synonyms WHERE synonym=? COLLATE NOCASE
          UNION ALL SELECT hpo_id,4 FROM hpo_terms WHERE hpo_id LIKE ? ESCAPE '!'
          UNION ALL SELECT hpo_id,5 FROM hpo_aliases WHERE alias_id LIKE ? ESCAPE '!'
          UNION ALL SELECT hpo_id,6 FROM hpo_terms WHERE name LIKE ? ESCAPE '!' COLLATE NOCASE
          UNION ALL SELECT hpo_id,7 FROM hpo_synonyms WHERE synonym LIKE ? ESCAPE '!' COLLATE NOCASE
          UNION ALL SELECT hpo_id,8 FROM hpo_terms WHERE name LIKE ? ESCAPE '!' COLLATE NOCASE
          UNION ALL SELECT hpo_id,9 FROM hpo_synonyms WHERE synonym LIKE ? ESCAPE '!' COLLATE NOCASE
        )
        SELECT h.hpo_id,h.name,h.is_obsolete
        FROM hpo_terms h
        JOIN (SELECT hpo_id, MIN(priority) AS priority FROM matches GROUP BY hpo_id) m
          ON m.hpo_id=h.hpo_id
        ORDER BY h.is_obsolete,m.priority,h.name COLLATE NOCASE,h.hpo_id
        LIMIT ?"""
    rows = conn.execute(sql, (
        query, query, query, query, prefix, prefix, prefix, prefix,
        contains, contains, limit,
    )).fetchall()
    return [dict(row) for row in rows]


def search_diseases(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    limit = _limit(limit)
    if not isinstance(query, str):
        raise ValueError("query must be text")
    query = query.strip()
    if not query:
        return []
    q = _pattern(query)
    rows = conn.execute(
        """SELECT disease_id,name FROM diseases
           WHERE disease_id LIKE ? ESCAPE '!' OR name LIKE ? ESCAPE '!' COLLATE NOCASE
           ORDER BY CASE WHEN disease_id=? THEN 0
                         WHEN name=? COLLATE NOCASE THEN 1
                         WHEN disease_id LIKE ? ESCAPE '!' THEN 2
                         WHEN name LIKE ? ESCAPE '!' COLLATE NOCASE THEN 3
                         ELSE 4 END, name COLLATE NOCASE,disease_id
           LIMIT ?""", (f"{q}%", f"%{q}%", query, query, f"{q}%", f"{q}%", limit),
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
                  p.reference_id,p.onset,p.sex,p.modifier,p.aspect,p.biocuration
           FROM disease_phenotypes p JOIN hpo_terms t ON p.hpo_id=t.hpo_id
           WHERE p.disease_id=? ORDER BY p.is_negated,p.hpo_id,p.annotation_id""",
        (disease_id,),
    ).fetchall()
    return {**dict(disease), "phenotypes": [dict(row) for row in annotations]}


def load_ranking_inputs(conn: sqlite3.Connection, *, phenotypic_only: bool = True) -> tuple[dict, dict, dict, dict]:
    """Return profiles, explicitly negated profiles, labels and parent IDs.

    These shapes are compatible with the existing phenotype ranking code.
    Multiple evidence records for the same disease/phenotype collapse to a set.
    By default, only aspect P (phenotypic abnormalities) enters the clinical
    phenotype ranking; inheritance/course/history remain available in the DB.
    Pass phenotypic_only=False to reproduce earlier all-aspect behavior.
    """
    profiles: dict[str, set[str]] = {}
    negatives: dict[str, set[str]] = {}
    labels: dict[str, str] = {}
    parents: dict[str, set[str]] = {}
    for r in conn.execute("SELECT disease_id,name FROM diseases"):
        labels[r["disease_id"]] = r["name"]
    annotation_query = "SELECT disease_id,hpo_id,is_negated FROM disease_phenotypes"
    if phenotypic_only:
        annotation_query += " WHERE aspect='P'"
    for r in conn.execute(annotation_query):
        target = negatives if r["is_negated"] else profiles
        target.setdefault(r["disease_id"], set()).add(r["hpo_id"])
    for r in conn.execute("SELECT child_id,parent_id FROM hpo_parents"):
        parents.setdefault(r["child_id"], set()).add(r["parent_id"])
    return profiles, negatives, labels, parents


def stats(conn: sqlite3.Connection) -> dict:
    tables = ("hpo_terms", "hpo_aliases", "hpo_synonyms", "hpo_parents",
              "diseases", "disease_phenotypes", "hpoa_source_rows")
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
