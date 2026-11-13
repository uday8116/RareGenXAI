from src.paired_stats import summarize


def test_paired_bootstrap_identical_methods_zero_difference():
    rows = []
    for case, score in [("a", 1), ("b", 0), ("c", 1)]:
        for method in ("overlap", "xgboost"):
            rows.append({"case_id": case, "method": method,
                         "top1": score, "top5": score, "reciprocal_rank": score})
    result = summarize(rows, replicates=100, seed=7)
    assert len(result) == 6
    assert all(row["difference"] == row["ci95_low"] == row["ci95_high"] == 0 for row in result)


def test_paired_bootstrap_reports_matched_cases_only():
    rows = [{"case_id": "a", "method": "overlap", "top1": 0, "top5": 0, "reciprocal_rank": 0},
            {"case_id": "a", "method": "xgboost", "top1": 1, "top5": 1, "reciprocal_rank": 1},
            {"case_id": "b", "method": "xgboost", "top1": 0, "top5": 0, "reciprocal_rank": 0}]
    result = summarize(rows, replicates=50)
    assert all(r["n"] == 1 for r in result)
    assert all(r["difference"] == 1 for r in result if r["method"] == "xgboost")
