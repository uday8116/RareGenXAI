"""Integration check using downloaded official files, skipped without a local DB."""
from pathlib import Path

import pytest
from src.db_access import connect_readonly, search_phenotypes, search_diseases
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
