import pytest
from src.ranking import ancestors, information_content, rank, semantic_similarity

PARENTS = {"HP:1": set(), "HP:2": {"HP:1"}, "HP:3": {"HP:1"}}
PROFILES = {"D1": {"HP:2"}, "D2": {"HP:3"}}
IC = information_content(PROFILES, PARENTS)

def test_ancestors():
    assert ancestors("HP:2", PARENTS) == {"HP:1", "HP:2"}

def test_exact_match():
    assert semantic_similarity("HP:2", "HP:2", PARENTS, IC) == 1.0

def test_top_disease():
    results = rank([("HP:2", "confirmed_present")], PROFILES, PARENTS, IC)
    assert results[0]["disease_id"] == "D1"

def test_unknown_ignored():
    assert rank([("HP:2", "unknown")], PROFILES, PARENTS, IC) == []

def test_suspected_weight():
    result = rank([("HP:2", "confirmed_present"), ("HP:3", "suspected_present")],
                  PROFILES, PARENTS, IC, top_k=2)
    assert result[0]["disease_id"] == "D1"

def test_absent_penalty():
    result = rank([("HP:2", "confirmed_present"), ("HP:3", "confirmed_absent")],
                  PROFILES, PARENTS, IC, top_k=2)
    assert result[0]["disease_id"] == "D1"

def test_bad_status():
    with pytest.raises(ValueError):
        rank([("HP:2", "maybe")], PROFILES, PARENTS, IC)
