"""Phase 2 regression tests using a small synthetic HPO ontology and annotation set."""
import hashlib
import json
import sqlite3

import pytest

from src.db_access import (
    connect_readonly, disease_detail, load_ranking_inputs,
    phenotype, search_diseases, search_phenotypes, stats,
)
from src.knowledge_db import build_database, validate_connection, verify_sources


def create_sample_hpo(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    ontology = """format-version: 1.2
ontology: hp

[Term]
id: HP:0000001
name: All

[Term]
id: HP:0000118
name: Phenotypic abnormality
is_a: HP:0000001 ! All

[Term]
id: HP:0001250
name: Seizure
alt_id: HP:0099999
synonym: "Convulsion" EXACT []
is_a: HP:0000118 ! Phenotypic abnormality

[Term]
id: HP:0001263
name: Global developmental delay
is_a: HP:0000118 ! Phenotypic abnormality

[Term]
id: HP:0000006
name: Autosomal dominant inheritance
is_a: HP:0000001 ! All
"""
    records = """database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\tfrequency\tsex\tmodifier\taspect\tbiocuration
MIM:1234\tExample syndrome A\t\tHP:0001250\tPMID:1\tPCS\t\t80%\t\t\tP\tHPO:Example
MIM:1234\tExample syndrome A\t\tHP:0001250\tPMID:1\tPCS\t\t80%\t\t\tP\tHPO:Example
MIM:1234\tExample syndrome A\tNOT\tHP:0001263\tPMID:2\tTAS\t\t0/10\t\t\tP\tHPO:Example
ORPHA:10\tExample syndrome B\t\tHP:0099999\tPMID:3\tPCS\t\t50%\t\t\tP\tHPO:Example
ORPHA:10\tExample syndrome B\t\tHP:0001263\tPMID:4\tPCS\t\t50%\t\t\tP\tHPO:Example
"""
    (raw / "hp.obo").write_text(ontology, encoding="utf-8")
    (raw / "phenotype.hpoa").write_text(records, encoding="utf-8")
    manifest = {}
    for name in ("hp.obo", "phenotype.hpoa"):
        path = raw / name
        manifest[name] = {
            "url": "https://purl.obolibrary.org/obo/" + name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
    (raw / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return raw


@pytest.fixture
def sample(tmp_path):
    raw = create_sample_hpo(tmp_path)
    db = tmp_path / "knowledge.sqlite3"
    return raw, db


def test_import_and_verify(sample):
    raw, db = sample
    build_database(raw, db)
    with connect_readonly(db) as conn:
        report = validate_connection(conn)
        assert report["counts"]["hpo_terms"] == 5
        assert report["counts"]["diseases"] == 2
        assert report["counts"]["disease_phenotypes"] == 4
        assert report["counts"]["negative_annotations"] == 1
        assert report["counts"]["hpo_parents"] >= 2
        assert report["metadata"]["unmapped_annotations"] == "0"
        source_hashes = {s["filename"]: s["sha256"] for s in report["sources"]}
        assert source_hashes["hp.obo"] == verify_sources(raw)["hp.obo"]["sha256"]
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_search_alias_synonym_and_parents(sample):
    raw, db = sample
    build_database(raw, db)
    with connect_readonly(db) as conn:
        assert phenotype(conn, "HP:0099999")["hpo_id"] == "HP:0001250"
        assert search_phenotypes(conn, "Convulsion")[0]["hpo_id"] == "HP:0001250"
        assert search_phenotypes(conn, "developmental")[0]["hpo_id"] == "HP:0001263"
        assert search_diseases(conn, "syndrome A")[0]["disease_id"] == "MIM:1234"
        assert search_diseases(conn, "%") == []
        assert search_phenotypes(conn, "%") == []
        assert search_phenotypes(conn, "") == []
        with pytest.raises(ValueError, match="limit"):
            search_phenotypes(conn, "seizure", limit=101)
        profiles, negatives, labels, parents = load_ranking_inputs(conn)
        assert profiles["ORPHA:10"] == {"HP:0001250", "HP:0001263"}
        assert negatives["MIM:1234"] == {"HP:0001263"}
        assert labels["MIM:1234"] == "Example syndrome A"
        assert "HP:0000118" in parents["HP:0001250"]


def test_preserve_negated_evidence_and_frequency(sample):
    raw, db = sample
    build_database(raw, db)
    with connect_readonly(db) as conn:
        obj = disease_detail(conn, "MIM:1234")
        assert len(obj["phenotypes"]) == 2
        assert obj["phenotypes"][1]["is_negated"] == 1
        assert obj["phenotypes"][1]["frequency"] == "0/10"
        assert disease_detail(conn, "unknown") is None


def test_no_clobber_on_invalid_manifest(sample):
    raw, db = sample
    build_database(raw, db)
    original = db.read_bytes()
    (raw / "hp.obo").write_text("corrupted", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum/length mismatch"):
        build_database(raw, db, replace=True)
    assert db.read_bytes() == original
    assert not list(db.parent.glob(".*.tmp"))


def test_requires_explicit_replace(sample):
    raw, db = sample
    build_database(raw, db)
    with pytest.raises(FileExistsError):
        build_database(raw, db)
    result = build_database(raw, db, replace=True)
    assert result["counts"]["diseases"] == 2


def test_invalid_qualifier_does_not_produce_database(sample):
    raw, db = sample
    hpoa = raw / "phenotype.hpoa"
    modified = hpoa.read_text().replace("\tNOT\t", "\tMAYBE\t")
    hpoa.write_text(modified)
    manifest = json.loads((raw / "manifest.json").read_text())
    manifest["phenotype.hpoa"]["sha256"] = hashlib.sha256(hpoa.read_bytes()).hexdigest()
    manifest["phenotype.hpoa"]["bytes"] = hpoa.stat().st_size
    (raw / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unknown HPOA qualifier"):
        build_database(raw, db)
    assert not db.exists()


def test_readonly_connection_rejects_writes(sample):
    raw, db = sample
    build_database(raw, db)
    with connect_readonly(db) as conn:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM diseases")
        assert stats(conn)["counts"]["diseases"] == 2


def test_missing_database_is_clear_error(sample):
    _, db = sample
    with pytest.raises(FileNotFoundError, match="Run:"):
        connect_readonly(db)
