"""Strict validation of saved synthetic, disease-disjoint evaluation records.

Reject missing/duplicate disease-method-missingness combinations, inconsistent
ranks and inflated metrics. Synthetic results are NOT clinical diagnostic accuracy.
"""
from __future__ import annotations

import math

from src.model_bundle import METHODS

MISSING_RATES = (0.0, 0.2, 0.4, 0.6)
METRICS = ("top1", "top5", "mrr", "candidate_recall")


def _integer(value: object, label: str) -> int:
    try:
        result = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {label}: {value!r}") from exc
    return result


def _number(value: object, label: str) -> float:
    try:
        result = float(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {label}: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"Non-finite {label}: {value!r}")
    return result


def audit_synthetic_results(
    summary: list[dict], trials: list[dict], heldout_ids: set[str],
) -> dict:
    """Recompute aggregates from individual held-out disease trials.

    The full Cartesian product of disease IDs, missingness levels and methods
    is required. All five methods share one retrieved candidate shortlist.
    """
    if not heldout_ids:
        raise ValueError("No held-out diseases")
    expected = {
        (disease, rate, method)
        for disease in heldout_ids
        for rate in MISSING_RATES
        for method in METHODS
    }
    seen = {}
    retrieval_by_case = {}
    for row in trials:
        try:
            disease = str(row["disease"])
            rate = _number(row["missing_rate"], "missing_rate")
            method = str(row["method"])
            rank = _integer(row["rank"], "rank")
            top1 = _integer(row["top1"], "top1")
            top5 = _integer(row["top5"], "top5")
            retrieved = _integer(row["retrieved"], "retrieved")
            mrr = _number(row["mrr"], "mrr")
        except KeyError as exc:
            raise ValueError(f"Trial column missing: {exc}") from exc
        key = (disease, rate, method)
        if key not in expected or key in seen:
            raise ValueError(f"Unexpected or duplicated synthetic trial: {key}")
        if rank < 0 or top1 not in (0, 1) or top5 not in (0, 1) or retrieved not in (0, 1):
            raise ValueError(f"Invalid rank/indicator for {key}")
        if retrieved != int(rank > 0) or top1 != int(rank == 1) or top5 != int(0 < rank <= 5):
            raise ValueError(f"Rank/indicator mismatch for {key}")
        if not math.isclose(mrr, 1.0 / rank if rank else 0.0, abs_tol=1e-9, rel_tol=0):
            raise ValueError(f"Reciprocal-rank mismatch for {key}")
        retrieval_key = (disease, rate)
        if retrieval_key in retrieval_by_case and retrieval_by_case[retrieval_key] != retrieved:
            raise ValueError(f"Candidate retrieval differs between methods for {retrieval_key}")
        retrieval_by_case[retrieval_key] = retrieved
        seen[key] = {"top1": top1, "top5": top5, "mrr": mrr, "candidate_recall": retrieved}
    missing = expected - set(seen)
    if missing:
        raise ValueError(f"Missing synthetic trial rows: {len(missing)}")

    expected_summary = {(rate, method) for rate in MISSING_RATES for method in METHODS}
    summary_keys = set()
    for row in summary:
        try:
            rate = _number(row["missing_rate"], "summary missing_rate")
            method = str(row["method"])
            n = _integer(row["n"], "n")
        except KeyError as exc:
            raise ValueError(f"Summary column missing: {exc}") from exc
        key = (rate, method)
        if key not in expected_summary or key in summary_keys:
            raise ValueError(f"Unexpected or duplicate summary row: {key}")
        summary_keys.add(key)
        if n != len(heldout_ids):
            raise ValueError(f"Incorrect cohort size for {key}: {n}")
        for field in METRICS:
            measured = _number(row.get(field), field)
            actual = sum(
                seen[disease, rate, method][field] for disease in heldout_ids
            ) / len(heldout_ids)
            if not math.isclose(measured, actual, rel_tol=1e-9, abs_tol=1e-10):
                raise ValueError(
                    f"Summary {field} does not match trial rows for {key}: "
                    f"reported={measured}, recomputed={actual}"
                )
    if summary_keys != expected_summary:
        raise ValueError(
            f"Missing synthetic summary rows: {len(expected_summary - summary_keys)}"
        )
    return {
        "trial_rows": len(seen),
        "summary_rows": len(summary_keys),
        "unique_heldout_diseases": len(heldout_ids),
        "methods": list(METHODS),
        "missing_rates": list(MISSING_RATES),
    }
