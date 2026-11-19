"""Phase 3 correctness regressions: meaningful retrieval and audited metrics."""
from copy import deepcopy

import pytest

from src.evaluation_integrity import audit_synthetic_results
from src.ml import RareGenML


def test_retrieval_excludes_unrelated_diseases_and_breaks_boundary_ties_by_id():
    model = RareGenML({
        "C": {"HP:0000001", "HP:0000004"},
        "B": {"HP:0000001", "HP:0000003"},
        "A": {"HP:0000001", "HP:0000002"},
        "Z": {"HP:0000999", "HP:0000998"},
    })
    observations = [("HP:0000001", "confirmed_present")]
    assert [item[0] for item in model.retrieve(observations, k=2)] == ["A", "B"]
    assert [item[0] for item in model.retrieve(observations, k=40)] == ["A", "B", "C"]
    assert [item["disease_id"] for item in model.rank(observations, top_k=10)] == ["A", "B", "C"]
    assert model.retrieve([("HP:0000001", "confirmed_absent")], k=40) == []
    assert model.retrieve([("HP:9999999", "confirmed_present")], k=40) == []


@pytest.fixture(scope="module")
def trained_fixture():
    profiles = {
        f"D{i:03d}": {f"HP:{i * 11 + j + 100:07d}" for j in range(5)}
        for i in range(16)
    }
    model = RareGenML(profiles)
    trials, summary, metadata = model.train(
        seed=7, train_diseases=8, test_diseases=4,
        queries_per_disease=1, candidates=6,
    )
    return model, trials, summary, metadata


def test_training_can_sample_negatives_without_fabricating_inference_hits(trained_fixture):
    model, trials, summary, metadata = trained_fixture
    assert metadata["training_pairs"] >= 8 * 2
    assert metadata["retrieval_policy"] == "positive_tfidf_only_ties_by_disease_id"
    assert metadata["training_negative_policy"] == "seeded_uniform_padding_training_only"
    assert len(model.models) == 4
    # All models use a common shortlist on each held-out case.
    groups = {}
    for trial in trials:
        key = (trial["disease"], trial["missing_rate"])
        groups.setdefault(key, set()).add(trial["retrieved"])
    assert all(len(values) == 1 for values in groups.values())


def test_synthetic_csv_audit_recomputes_all_summary_metrics(trained_fixture):
    _, trials, summary, meta = trained_fixture
    report = audit_synthetic_results(summary, trials, set(meta["heldout_disease_ids"]))
    assert report["trial_rows"] == 80
    assert report["summary_rows"] == 20
    assert report["unique_heldout_diseases"] == 4


@pytest.mark.parametrize("field,value,pattern", [
    ("top1", 1, "Rank/indicator mismatch"),
    ("retrieved", 0, "Rank/indicator mismatch"),
    ("mrr", 0.4444444444, "Reciprocal-rank mismatch"),
])
def test_tampered_trial_fails_evaluation_audit(trained_fixture, field, value, pattern):
    _, trials, summary, meta = trained_fixture
    altered = deepcopy(trials)
    target = next(i for i, row in enumerate(altered) if row["rank"] == 1)
    altered[target][field] = value if field != "top1" else 0
    with pytest.raises(ValueError, match=pattern):
        audit_synthetic_results(summary, altered, set(meta["heldout_disease_ids"]))


def test_missing_trial_and_duplicate_summary_fail(trained_fixture):
    _, trials, summary, meta = trained_fixture
    heldout = set(meta["heldout_disease_ids"])
    with pytest.raises(ValueError, match="Missing synthetic trial"):
        audit_synthetic_results(summary, trials[:-1], heldout)
    with pytest.raises(ValueError, match="Unexpected or duplicate summary"):
        audit_synthetic_results(summary + [summary[0]], trials, heldout)


def test_falsified_summary_accuracy_fails(trained_fixture):
    _, trials, summary, meta = trained_fixture
    modified = deepcopy(summary)
    modified[0]["top1"] = 1.0 - float(modified[0]["top1"])
    # Should fail even when the summary is syntactically valid.
    with pytest.raises(ValueError, match="Summary top1 does not match"):
        audit_synthetic_results(modified, trials, set(meta["heldout_disease_ids"]))
