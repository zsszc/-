import math

from scripts.eval_logistics_retrieval import aggregate, load_cases, metrics_for_case


def _hit(section: str) -> dict:
    return {"section_path": section, "question": section}


def test_dataset_has_expected_shape_and_section_coverage():
    rows = load_cases()
    assert len(rows) == 30
    assert sum(row["kind"] == "single" for row in rows) == 19
    assert sum(row["kind"] == "multi" for row in rows) == 11
    assert len({section for row in rows for section in row["expected_sections"]}) == 19


def test_single_relevant_document_metrics():
    metrics = metrics_for_case([_hit("noise"), _hit("wanted")], ["wanted"])
    assert metrics["hit_rate_at_1"] == 0
    assert metrics["hit_rate_at_3"] == 1
    assert metrics["precision_at_3"] == 1 / 3
    assert metrics["recall_at_3"] == 1
    assert metrics["mrr_at_5"] == 0.5
    assert 0 < metrics["ndcg_at_5"] < 1


def test_multi_document_metrics_and_duplicate_section_deduplication():
    hits = [_hit("a"), _hit("a"), _hit("noise"), _hit("b")]
    metrics = metrics_for_case(hits, ["a", "b"])
    assert metrics["precision_at_5"] == 2 / 5
    assert metrics["recall_at_3"] == 0.5
    assert metrics["recall_at_5"] == 1
    assert metrics["mrr_at_5"] == 1
    expected = (1 + 1 / math.log2(5)) / (1 + 1 / math.log2(3))
    assert math.isclose(metrics["ndcg_at_5"], expected)


def test_aggregate_averages_each_metric():
    first = metrics_for_case([_hit("a")], ["a"])
    second = metrics_for_case([], ["a"])
    result = aggregate([first, second])
    assert result["recall_at_5"] == 0.5
    assert result["mrr_at_5"] == 0.5
