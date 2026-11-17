"""Validate matched external benchmark and DeepRare inputs.

All case IDs must match exactly, with no missing, repeated, or empty predictions.
This module validates formatting, not the scientific provenance of predictions.
"""
import csv


def read_cases(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"case_id", "disease_id", "hpo_ids"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"Required columns: {sorted(required)}")
        rows = list(reader)
    if not rows:
        raise ValueError("No cases found")
    ids = [str(r.get("case_id") or "").strip() for r in rows]
    if any(not value for value in ids):
        raise ValueError("Empty case ID")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate case IDs")
    for row, case_id in zip(rows, ids):
        row["case_id"] = case_id
        row["disease_id"] = str(row.get("disease_id") or "").strip()
        if not row["disease_id"]:
            raise ValueError(f"Case {case_id} has no disease ID")
        terms = [v.strip() for v in str(row.get("hpo_ids") or "").split(";") if v.strip()]
        if not terms or any(not term.startswith("HP:") for term in terms):
            raise ValueError(f"Case {case_id} has missing or malformed HPO IDs")
    return rows


def read_matched_predictions(path, expected_case_ids):
    expected = set(expected_case_ids)
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"case_id", "ranked_disease_ids"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"DeepRare CSV must have columns: {sorted(required)}")
        predictions = {}
        for row in reader:
            case_id = str(row.get("case_id") or "").strip()
            if not case_id:
                raise ValueError("DeepRare prediction has an empty case ID")
            if case_id in predictions:
                raise ValueError(f"Duplicate DeepRare case ID: {case_id}")
            raw = str(row.get("ranked_disease_ids") or "")
            ids = [value.strip() for value in raw.split(";")]
            if any(not disease for disease in ids):
                raise ValueError(f"Empty ranked disease ID for case {case_id}")
            if len(set(ids)) != len(ids):
                raise ValueError(f"Repeated ranked disease ID for case {case_id}")
            predictions[case_id] = ids
    if set(predictions) != expected:
        missing = sorted(expected - set(predictions))
        extra = sorted(set(predictions) - expected)
        raise ValueError(
            "DeepRare case IDs must match exactly; "
            f"missing={missing[:10]}, extra={extra[:10]}"
        )
    return predictions
