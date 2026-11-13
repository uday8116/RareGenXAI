import pytest
from src.gnn import HPOGraphReranker

torch = pytest.importorskip("torch")

PROFILES = {
    f"D{i}": {f"HP:{1000 + i * 10 + j:07d}" for j in range(4)}
    for i in range(8)
}


def test_gnn_trains_and_ranks():
    model = HPOGraphReranker(PROFILES, {}, hidden=8, seed=3)
    with pytest.raises(ValueError, match="not trained"):
        model.rank([(sorted(PROFILES["D0"])[0], "confirmed_present")])
    result = model.fit(seed=3, train_diseases=4, queries_per_disease=1,
                       candidates=5, epochs=1)
    assert result["training_queries"] == 4
    rows = model.rank([(sorted(PROFILES["D0"])[0], "confirmed_present")], top_k=3)
    assert rows and len(rows) <= 3
    assert model.rank([("HP:0000001", "confirmed_absent")]) == []
