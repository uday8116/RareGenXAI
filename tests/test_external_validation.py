"""Regression tests for external benchmark input integrity."""
import csv
import pytest
from src.external_validation import read_cases, read_matched_predictions


def write_csv(tmp_path, name, fieldnames, rows):
    path = tmp_path / name
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_cases_valid(tmp_path):
    path = write_csv(tmp_path, "cases.csv", ["case_id", "disease_id", "hpo_ids"],
                     [{"case_id": " c1 ", "disease_id": "OMIM:1", "hpo_ids": "HP:0000001;HP:0000002"}])
    assert read_cases(path)[0]["case_id"] == "c1"


@pytest.mark.parametrize("rows,match", [
    ([{"case_id": "a", "disease_id": "OMIM:1", "hpo_ids": "HP:0000001"},
      {"case_id": "a", "disease_id": "OMIM:2", "hpo_ids": "HP:0000002"}], "Duplicate"),
    ([{"case_id": "", "disease_id": "OMIM:1", "hpo_ids": "HP:0000001"}], "Empty"),
    ([{"case_id": "a", "disease_id": "OMIM:1", "hpo_ids": ""}], "HPO"),
    ([{"case_id": "a", "disease_id": "", "hpo_ids": "HP:0000001"}], "disease"),
])
def test_invalid_cases(tmp_path, rows, match):
    path = write_csv(tmp_path, "cases.csv", ["case_id", "disease_id", "hpo_ids"], rows)
    with pytest.raises(ValueError, match=match):
        read_cases(path)


def test_deeprare_matched(tmp_path):
    path = write_csv(tmp_path, "deeprare.csv", ["case_id", "ranked_disease_ids"],
                     [{"case_id": "a", "ranked_disease_ids": " OMIM:1 ; OMIM:2 "},
                      {"case_id": "b", "ranked_disease_ids": "OMIM:2"}])
    assert read_matched_predictions(path, {"a", "b"}) == {
        "a": ["OMIM:1", "OMIM:2"], "b": ["OMIM:2"]
    }


@pytest.mark.parametrize("rows,match", [
    ([{"case_id": "a", "ranked_disease_ids": "OMIM:1"},
      {"case_id": "a", "ranked_disease_ids": "OMIM:2"}], "Duplicate"),
    ([{"case_id": "a", "ranked_disease_ids": ""}], "Empty"),
    ([{"case_id": "a", "ranked_disease_ids": "OMIM:1;OMIM:1"}], "Repeated"),
    ([{"case_id": "b", "ranked_disease_ids": "OMIM:1"}], "match exactly"),
])
def test_invalid_deeprare(tmp_path, rows, match):
    path = write_csv(tmp_path, "deeprare.csv", ["case_id", "ranked_disease_ids"], rows)
    with pytest.raises(ValueError, match=match):
        read_matched_predictions(path, {"a"})
