"""Versioned schema for the *local-only*, read-only-at-inference HPO knowledge base.

No patient records or identifiable clinical information are stored here.
"""
import sqlite3

SCHEMA_VERSION = 1

MIGRATIONS = {
    1: """
    CREATE TABLE schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL
    );
    CREATE TABLE data_sources (
        filename TEXT PRIMARY KEY,
        source_url TEXT NOT NULL,
        sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
        byte_count INTEGER NOT NULL CHECK (byte_count > 0)
    );
    CREATE TABLE db_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE hpo_terms (
        hpo_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        definition TEXT NOT NULL DEFAULT '',
        is_obsolete INTEGER NOT NULL DEFAULT 0 CHECK(is_obsolete IN (0,1))
    );
    CREATE TABLE hpo_aliases (
        alias_id TEXT PRIMARY KEY,
        hpo_id TEXT NOT NULL REFERENCES hpo_terms(hpo_id)
    );
    CREATE TABLE hpo_synonyms (
        hpo_id TEXT NOT NULL REFERENCES hpo_terms(hpo_id),
        synonym TEXT NOT NULL,
        PRIMARY KEY (hpo_id, synonym)
    );
    CREATE TABLE hpo_parents (
        child_id TEXT NOT NULL REFERENCES hpo_terms(hpo_id),
        parent_id TEXT NOT NULL REFERENCES hpo_terms(hpo_id),
        PRIMARY KEY (child_id, parent_id),
        CHECK(child_id <> parent_id)
    );
    CREATE TABLE diseases (
        disease_id TEXT PRIMARY KEY,
        name TEXT NOT NULL
    );
    CREATE TABLE disease_phenotypes (
        annotation_id INTEGER PRIMARY KEY,
        disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
        hpo_id TEXT NOT NULL REFERENCES hpo_terms(hpo_id),
        is_negated INTEGER NOT NULL CHECK(is_negated IN (0,1)),
        evidence_code TEXT NOT NULL DEFAULT '',
        reference_id TEXT NOT NULL DEFAULT '',
        frequency TEXT NOT NULL DEFAULT '',
        onset TEXT NOT NULL DEFAULT '',
        sex TEXT NOT NULL DEFAULT '',
        aspect TEXT NOT NULL DEFAULT '',
        UNIQUE(disease_id,hpo_id,is_negated,evidence_code,reference_id,frequency,onset,sex,aspect)
    );
    CREATE INDEX idx_hpo_name ON hpo_terms(name COLLATE NOCASE);
    CREATE INDEX idx_hpo_synonym ON hpo_synonyms(synonym COLLATE NOCASE);
    CREATE INDEX idx_hpo_parent ON hpo_parents(parent_id);
    CREATE INDEX idx_disease_name ON diseases(name COLLATE NOCASE);
    CREATE INDEX idx_annotations_disease ON disease_phenotypes(disease_id);
    CREATE INDEX idx_annotations_hpo ON disease_phenotypes(hpo_id);
    """,
}


def apply_migrations(connection: sqlite3.Connection) -> None:
    """Apply forward-only schema migrations to an empty/staged database.

    This importer builds a fresh staging DB and swaps it into place, so existing
    data is never mutated while the new release is being parsed.
    """
    current = connection.execute("PRAGMA user_version").fetchone()[0]
    if current > SCHEMA_VERSION:
        raise ValueError(f"Database schema {current} is newer than supported {SCHEMA_VERSION}")
    for version in range(current + 1, SCHEMA_VERSION + 1):
        connection.executescript(MIGRATIONS[version])
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
            (version,),
        )
        connection.execute(f"PRAGMA user_version = {version}")
        connection.commit()
