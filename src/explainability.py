"""Phase 6: deterministic HPO evidence trace for a *single* candidate disease.

This is an explanation of the ontology/overlap ranking calculation, not SHAP,
a calibrated diagnostic probability, a causal claim or a model explanation.
ML methods receive *ontology context only*; do not interpret these entries as
feature importance of an XGBoost / MLP / Random Forest decision.
"""
from __future__ import annotations

from src.ranking import WEIGHTS, ancestors, semantic_similarity

BASELINE_METHODS = frozenset({"overlap", "semantic"})
ALL_METHODS = BASELINE_METHODS | frozenset({
    "tfidf", "logistic", "random_forest", "xgboost", "mlp",
})


def explain_candidate(
    observations,
    disease_id,
    profiles,
    parents,
    ic,
    *,
    method="overlap",
    quality=True,
    labels=None,
):
    """Map each observation to an annotated disease HPO term and score impact.

    The numeric contribution for ontology baselines follows src.ranking.rank
    exactly (same denominator, evidence weights and six-decimal rounding).
    The best ontology match and most informative shared ancestor use stable
    HPO-ID tie-breaking to make the explanation reproducible.

    Returns evidence and a baseline *per-disease* score, which need not be a
    candidate in the global top-k. ML methods deliberately have no numeric
    per-term contributions or reconstructed ML scores.
    """
    if method not in ALL_METHODS:
        raise ValueError("Unsupported ranking method")
    if disease_id not in profiles:
        raise ValueError("Unknown disease candidate")
    if any(status not in WEIGHTS for _, status in observations):
        raise ValueError("Invalid evidence status")

    disease_terms = sorted(profiles[disease_id])
    denominator = sum(
        (abs(WEIGHTS[status]) if quality else 1.0)
        for _, status in observations
        if status != "unknown" and (quality or status.endswith("present"))
    )
    baseline = method in BASELINE_METHODS
    rows = []

    for term, status in observations:
        best_id = None
        best_score = 0.0
        shared = None

        if method == "semantic":
            query_ancestors = ancestors(term, parents)
            for candidate in disease_terms:
                score = semantic_similarity(term, candidate, parents, ic)
                if score > best_score:
                    best_score = score
                    best_id = candidate
            if best_id is not None:
                common = query_ancestors & ancestors(best_id, parents)
                if common:
                    shared = sorted(common, key=lambda hpo: (-ic.get(hpo, 0.0), hpo))[0]
        elif term in profiles[disease_id]:
            best_id = term
            best_score = 1.0
            shared = term

        if best_score <= 0:
            relation = "none"
            best_id = None
            shared = None
        elif best_id == term:
            relation = "exact"
        else:
            relation = "ontology_related"

        weight = (WEIGHTS[status] if quality else
                  (1.0 if status.endswith("present") else 0.0))
        contribution = (
            round(weight * best_score / denominator, 6)
            if baseline and denominator else None
        )
        rows.append({
            "hpo_id": term,
            "status": status,
            "relation": relation,
            "best_disease_hpo_id": best_id,
            "shared_ancestor_hpo_id": shared if method == "semantic" else None,
            "match": round(best_score, 4),
            # Do not confuse the input quality weight with ML feature importance.
            "evidence_weight": round(weight, 4) if baseline else None,
            "contribution": contribution,
        })

    score = round(sum(row["contribution"] or 0.0 for row in rows), 6) if baseline else None
    return {
        "method": method,
        "disease_id": disease_id,
        "disease_name": (labels or {}).get(disease_id, disease_id),
        "explanation_type": "signed_ontology_contributions" if baseline else "ontology_context_not_ml_attribution",
        "evidence": rows,
        "reconstructed_baseline_score": score,
        "model_sha256": None,
        "disclaimer": (
            "Ontology evidence is a research ranking trace, not a diagnosis, "
            "calibrated probability, SHAP value or causal explanation. "
            "Model feature weights and SHAP attributions are not computed."
        ),
    }
