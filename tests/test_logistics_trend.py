import pytest

from scripts import eval_logistics_trend as trend


def test_metrics_require_complete_successful_logistics_run():
    summary = {"errors": 0, "overall": {"recall_at_5": 0.96,
                                        "mrr_at_5": 0.94, "ndcg_at_5": 0.93}}
    assert trend.metrics_from_summary(summary, sample_count=30) == {
        "dataset": "logistics_retrieval_v1", "recall_at_5": 0.96,
        "mrr_at_5": 0.94, "ndcg_at_5": 0.93,
    }
    with pytest.raises(RuntimeError, match="不写趋势"):
        trend.metrics_from_summary({**summary, "errors": 1}, sample_count=30)
    with pytest.raises(ValueError, match="不写趋势"):
        trend.metrics_from_summary(summary, sample_count=29)


@pytest.mark.asyncio
async def test_run_does_not_insert_when_retrieval_has_errors(monkeypatch):
    async def fake_evaluate(*args, **kwargs):
        return {"errors": 1, "overall": {}}, []

    async def forbidden_insert(*args, **kwargs):
        raise AssertionError("failed evaluation must not be persisted")

    monkeypatch.setattr(trend, "evaluate_strategy", fake_evaluate)
    monkeypatch.setattr(trend.repository, "insert_eval_run", forbidden_insert)
    with pytest.raises(RuntimeError, match="不写趋势"):
        await trend.run_once("手动")
