"""Integration check using downloaded official files, skipped without a local DB."""
import json
from pathlib import Path

import pytest
from src.db_access import connect_readonly, search_phenotypes, search_diseases, load_ranking_inputs
from src.knowledge_db import validate_connection

DATABASE = Path("data/local/raregen.sqlite3")


@pytest.mark.skipif(not DATABASE.exists(), reason="Run python -m src.knowledge_db build first")
def test_official_knowledge_import():
    with connect_readonly(DATABASE) as conn:
        result = validate_connection(conn)
        assert result["counts"]["hpo_terms"] > 10000
        assert result["counts"]["diseases"] > 1000
        assert result["counts"]["disease_phenotypes"] > 10000
        assert search_phenotypes(conn, "HP:0001250")
        assert search_diseases(conn, "ORPHA")
        assert result["counts"]["hpoa_source_rows"] >= result["counts"]["disease_phenotypes"]
        assert result["counts"]["hpoa_source_rows"] == int(result["metadata"]["annotation_rows_read"])
        assert int(result["metadata"]["duplicate_annotations"]) == (
            result["counts"]["hpoa_source_rows"] - result["counts"]["disease_phenotypes"]
        )
        # Compare both positive and negative sets to the original legacy
        # profiles (after mapping alternate HPO IDs to canonical ones).
        legacy = json.loads(Path("data/processed/profiles.json").read_text())
        aliases = dict(conn.execute("SELECT alias_id,hpo_id FROM hpo_aliases").fetchall())
        profiles, negatives, _, _ = load_ranking_inputs(conn, phenotypic_only=False)
        for disease, terms in legacy["profiles"].items():
            assert profiles[disease] == {aliases.get(term, term) for term in terms}
        for disease, terms in legacy["negatives"].items():
            assert negatives[disease] == {aliases.get(term, term) for term in terms}

