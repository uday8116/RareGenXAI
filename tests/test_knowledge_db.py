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
from src.db_schema import apply_migrations, MIGRATIONS


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
        assert report["counts"]["hpoa_source_rows"] == 5
        assert report["metadata"]["duplicate_annotations"] == "1"
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
        assert obj["phenotypes"][0]["biocuration"] == "HPO:Example"
        assert obj["phenotypes"][0]["modifier"] == ""
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



def update_hpoa_manifest(raw):
    """Recompute only HPOA provenance after deliberate synthetic test edits."""
    file = raw / "phenotype.hpoa"
    manifest_path = raw / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["phenotype.hpoa"]["sha256"] = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest["phenotype.hpoa"]["bytes"] = file.stat().st_size
    manifest_path.write_text(json.dumps(manifest))


def test_strict_reader_catches_malformed_hpo_id(sample):
    raw, db = sample
    file = raw / "phenotype.hpoa"
    file.write_text(file.read_text().replace("\tHP:0001250\t", "\tBAD:001250\t", 1))
    update_hpoa_manifest(raw)
    with pytest.raises(ValueError, match="Invalid HPO ID"):
        build_database(raw, db)
    assert not db.exists()


def test_strict_reader_catches_unknown_valid_hpo_id(sample):
    raw, db = sample
    file = raw / "phenotype.hpoa"
    file.write_text(file.read_text().replace("\tHP:0001250\t", "\tHP:0999999\t", 1))
    update_hpoa_manifest(raw)
    with pytest.raises(ValueError, match="Unknown HPO term"):
        build_database(raw, db)
    assert not db.exists()


def test_strict_reader_rejects_schema_drift(sample):
    raw, db = sample
    file = raw / "phenotype.hpoa"
    file.write_text(file.read_text().replace("\tbiocuration\n", "\n", 1))
    update_hpoa_manifest(raw)
    with pytest.raises(ValueError, match="format drift"):
        build_database(raw, db)


def test_modifiers_biocuration_and_raw_duplicate_rows_preserved(sample):
    raw, db = sample
    file = raw / "phenotype.hpoa"
    # Two records have the same phenotype/evidence, but unique clinical modifier
    # and biocuration history, so they must no longer collapse into one.
    rows = file.read_text().splitlines()
    fields = rows[2].split("\t")
    fields[9] = "HP:0031796"
    fields[11] = "HPO:Reviewer[2025-01-01]"
    rows[2] = "\t".join(fields)
    file.write_text("\n".join(rows) + "\n")
    update_hpoa_manifest(raw)
    build_database(raw, db)
    with connect_readonly(db) as conn:
        report = validate_connection(conn, raw_dir=raw)
        assert report["counts"]["hpoa_source_rows"] == 5
        assert report["counts"]["disease_phenotypes"] == 5
        assert report["metadata"]["duplicate_annotations"] == "0"
        assert conn.execute(
            "SELECT COUNT(*) FROM hpoa_source_rows WHERE disease_id='MIM:1234'"
        ).fetchone()[0] == 3
        assert conn.execute(
            "SELECT COUNT(*) FROM disease_phenotypes WHERE modifier='HP:0031796'"
        ).fetchone()[0] == 1
        assert disease_detail(conn, "MIM:1234")["phenotypes"][1]["biocuration"] == (
            "HPO:Reviewer[2025-01-01]"
        )


def test_database_provenance_must_match_official_source_snapshot(sample):
    raw, db = sample
    build_database(raw, db)
    ontology_file = raw / "hp.obo"
    ontology_file.write_text(ontology_file.read_text() + "\nremark: legitimate revised copy\n")
    manifest_path = raw / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["hp.obo"]["sha256"] = hashlib.sha256(ontology_file.read_bytes()).hexdigest()
    manifest["hp.obo"]["bytes"] = ontology_file.stat().st_size
    manifest_path.write_text(json.dumps(manifest))
    with connect_readonly(db) as conn:
        with pytest.raises(ValueError, match="provenance differs"):
            validate_connection(conn, raw_dir=raw)


def test_clinical_ranking_excludes_inheritance_aspect_by_default(sample):
    raw, db = sample
    file = raw / "phenotype.hpoa"
    file.write_text(file.read_text() +
        "ORPHA:10\tExample syndrome B\t\tHP:0000006\tPMID:5\tPCS"
        "\t\t100%\t\t\tI\tHPO:Example\n")
    update_hpoa_manifest(raw)
    build_database(raw, db)
    with connect_readonly(db) as conn:
        profiles, _, _, _ = load_ranking_inputs(conn)
        all_profiles, _, _, _ = load_ranking_inputs(conn, phenotypic_only=False)
        assert "HP:0000006" not in profiles["ORPHA:10"]
        assert "HP:0000006" in all_profiles["ORPHA:10"]
        assert any(p["aspect"] == "I" for p in disease_detail(conn, "ORPHA:10")["phenotypes"])


def test_v1_to_v2_schema_migration_preserves_existing_annotation(tmp_path):
    conn = sqlite3.connect(tmp_path / "legacy.sqlite3")
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(MIGRATIONS[1])
        conn.execute("PRAGMA user_version=1")
        conn.execute("INSERT INTO hpo_terms(hpo_id,name) VALUES ('HP:0001250','Seizure')")
        conn.execute("INSERT INTO diseases(disease_id,name) VALUES ('MIM:1','Legacy')")
        conn.execute(
            """INSERT INTO disease_phenotypes(disease_id,hpo_id,is_negated,aspect)
               VALUES ('MIM:1','HP:0001250',0,'P')"""
        )
        conn.commit()
        apply_migrations(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        values = conn.execute(
            "SELECT disease_id,hpo_id,modifier,biocuration FROM disease_phenotypes"
        ).fetchone()
        assert values == ("MIM:1", "HP:0001250", "", "")
        assert conn.execute(
            "SELECT COUNT(*) FROM hpoa_source_rows"
        ).fetchone()[0] == 0  # source rows require --replace from official HPO
    finally:
        conn.close()
