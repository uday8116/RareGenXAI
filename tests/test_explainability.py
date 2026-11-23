"""Offline Phase 6 proof of ontology explanation semantics (no patient data)."""
import pytest

from src.explainability import explain_candidate
from src.ranking import rank


@pytest.fixture
def toy():
    parents = {
        "HP:0001250": {"HP:0000118"},
        "HP:0001263": {"HP:0000118"},
        "HP:0000118": {"HP:0000001"},
        "HP:0000001": set(),
    }
    profiles = {
        "MIM:1": {"HP:0001250"},
        "MIM:2": {"HP:0001263"},
    }
    # Controlled, positive information-content values to exercise MICA.
    ic = {"HP:0000001": 0.0, "HP:0000118": 0.3,
          "HP:0001250": 0.8, "HP:0001263": 0.9}
    return profiles, parents, ic


def test_overlap_matches_original_rank_sum_exactly(toy):
    profiles, parents, ic = toy
    observations = [
        ("HP:0001250", "confirmed_present"),
        ("HP:0001263", "confirmed_absent"),
        ("HP:0000118", "unknown"),
    ]
    response = explain_candidate(observations, "MIM:1", profiles, parents, ic,
                                 method="overlap")
    ranked = rank(observations, profiles, parents, ic, method="overlap", top_k=2)
    expected = next(row for row in ranked if row["disease_id"] == "MIM:1")
    assert response["reconstructed_baseline_score"] == expected["score"]
    assert response["evidence"][0]["relation"] == "exact"
    assert response["evidence"][0]["contribution"] > 0
    assert response["evidence"][1]["contribution"] == 0
    assert response["evidence"][2]["contribution"] == 0
    assert response["evidence"][2]["evidence_weight"] == 0


def test_confirmed_absent_penalizes_annotated_disease(toy):
    profiles, parents, ic = toy
    observations = [
        ("HP:0001263", "confirmed_present"),
        ("HP:0001250", "confirmed_absent"),
    ]
    explained = explain_candidate(observations, "MIM:1", profiles, parents, ic,
                                  method="overlap")
    assert explained["evidence"][1]["relation"] == "exact"
    assert explained["evidence"][1]["contribution"] < 0
    assert explained["reconstructed_baseline_score"] < 0


def test_semantic_uses_most_informative_common_ancestor(toy):
    profiles, parents, ic = toy
    observations = [("HP:0001263", "suspected_present")]
    described = explain_candidate(observations, "MIM:1", profiles, parents, ic,
                                  method="semantic")
    detail = described["evidence"][0]
    assert detail["relation"] == "ontology_related"
    assert detail["best_disease_hpo_id"] == "HP:0001250"
    assert detail["shared_ancestor_hpo_id"] == "HP:0000118"
    assert detail["match"] == round(0.3 / 0.9, 4)
    rank_score = rank(observations, profiles, parents, ic,
                      method="semantic", top_k=2)[1]["score"]
    assert described["reconstructed_baseline_score"] == rank_score


def test_quality_disabled_ignores_confirmed_absent(toy):
    profiles, parents, ic = toy
    observations = [("HP:0001250", "confirmed_present"),
                    ("HP:0001250", "confirmed_absent")]
    # Duplicate validation belongs to the API. The pure function must
    # reproduce the quality=False baseline weighting regardless.
    detail = explain_candidate(observations, "MIM:1", profiles, parents, ic,
                               quality=False, method="overlap")
    assert detail["evidence"][1]["contribution"] == 0
    assert detail["reconstructed_baseline_score"] == 1.0


def test_ml_explanation_is_context_only_never_shap(toy):
    profiles, parents, ic = toy
    output = explain_candidate([("HP:0001250", "confirmed_present")],
                               "MIM:1", profiles, parents, ic, method="xgboost")
    assert output["explanation_type"] == "ontology_context_not_ml_attribution"
    assert output["reconstructed_baseline_score"] is None
    assert output["evidence"][0]["contribution"] is None
    assert output["evidence"][0]["evidence_weight"] is None
    assert "SHAP" in output["disclaimer"]


def test_stable_tie_break_and_rejects_unknown_method(toy):
    profiles, parents, ic = toy
    profiles["MIM:3"] = {"HP:0001263", "HP:0001250"}
    detail = explain_candidate([("HP:0000118", "confirmed_present")],
                               "MIM:3", profiles, parents, ic,
                               method="semantic")["evidence"][0]
    assert detail["best_disease_hpo_id"] == "HP:0001250"
    with pytest.raises(ValueError, match="Unsupported"):
        explain_candidate([], "MIM:1", profiles, parents, ic, method="made-up")
    with pytest.raises(ValueError, match="Unknown disease"):
        explain_candidate([], "MIM:999", profiles, parents, ic)


def test_empty_or_unknown_observations_cannot_invent_score(toy):
    profiles, parents, ic = toy
    detail = explain_candidate([("HP:0001250", "unknown")],
                               "MIM:1", profiles, parents, ic, method="overlap")
    assert detail["reconstructed_baseline_score"] == 0
    assert all(x["contribution"] is None for x in detail["evidence"])
