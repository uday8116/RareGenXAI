import random
import pytest
from src.ml import RareGenML, synthetic_observations

PROFILES = {
    f"D{i}": {f"HP:{200 + ((i * 7 + j * 3) % 97):07d}" for j in range(6)}
    for i in range(25)
}


def test_retrieve_matches_exact_phenotype():
    ml = RareGenML(PROFILES)
    term = sorted(PROFILES["D0"])[0]
    result = ml.retrieve([(term, "confirmed_present")])
    assert result and any(d == "D0" for d, _ in result)


def test_negative_only_returns_no_results():
    ml = RareGenML(PROFILES)
    assert ml.rank([("HP:0000001", "confirmed_absent")]) == []


def test_unknown_model_rejected():
    ml = RareGenML(PROFILES)
    with pytest.raises(ValueError):
        ml.rank([("HP:0000001", "confirmed_present")], model="invalid")


def test_train_and_rank():
    ml = RareGenML(PROFILES)
    details, summary, meta = ml.train(seed=7, train_diseases=12, test_diseases=4,
                                      queries_per_disease=1, candidates=12)
    assert meta["heldout_diseases"] == 4
    assert len(details) == 4 * 4 * 3
    assert len(summary) == 12
    assert all(0 <= x["top1"] <= 1 for x in summary)
    assert set(ml.models) == {"logistic", "random_forest"}
    query = synthetic_observations("D0", PROFILES, random.Random(5))
    assert ml.rank(query, model="random_forest", top_k=5)


def test_absent_feature_does_not_equal_unknown():
    ml = RareGenML(PROFILES)
    term = sorted(PROFILES["D0"])[0]
    absent = ml.features([(term, "confirmed_absent")], "D0", 0.0)
    unknown = ml.features([(term, "unknown")], "D0", 0.0)
    assert absent[4] == 1.0 and unknown[4] == 0.0
