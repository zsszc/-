from collections import Counter
import json

import pytest

from scripts import eval_logistics_agent as evaluator
from scripts.eval_logistics_agent import load_cases, score_case, select_cases, summarize


def test_evaluator_loads_current_300_case_distribution():
    cases = load_cases()
    assert len(cases) == 300


def test_evaluator_scores_tool_alias_and_abstention():
    cases = load_cases()
    tool_case = next(case for case in cases if case["category"] == "tool_operation" and "ticket_draft" in case["expected_tools"])
    passed, _ = score_case(tool_case, {"tool_calls": [{"name": "create_ticket"}], "answer": "已生成工单"})
    assert passed

    abstain_case = next(case for case in cases if case["category"] == "out_of_scope")
    passed, _ = score_case(abstain_case, {"tool_calls": [], "answer": "这个问题超出当前知识范围，建议转人工。", "suggested_actions": []})
    assert passed


def test_evaluator_summarizes_by_category():
    summary = summarize([
        {"category": "tool_operation", "passed": True},
        {"category": "tool_operation", "passed": False},
    ])
    assert summary["by_category"]["tool_operation"] == {"total": 2, "passed": 1, "pass_rate": 0.5}


def test_limited_online_sample_is_category_balanced():
    selected = select_cases(load_cases(), 50)
    assert len(selected) == 50
    assert Counter(case["category"] for case in selected) == Counter({
        "policy_process": 10, "cross_document": 10, "tool_operation": 10,
        "out_of_scope": 10, "boundary_clarification": 10,
    })


@pytest.mark.asyncio
async def test_online_report_checkpoints_and_resumes(monkeypatch, tmp_path):
    cases = load_cases()[:3]
    report_path = tmp_path / "logistics_agent_eval_report_live_v5.json"
    calls = 0

    async def interrupted(batch, base_url, concurrency):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("interrupted")
        return [{"id": case["id"], "category": case["category"],
                 "passed": True, "reason": "ok", "response": {}} for case in batch]

    monkeypatch.setattr(evaluator, "evaluate_live", interrupted)
    with pytest.raises(RuntimeError, match="interrupted"):
        await evaluator.evaluate_with_checkpoints(
            cases, "http://127.0.0.1:8000", report_path,
            concurrency=1, batch_size=2)
    partial = json.loads(report_path.read_text(encoding="utf-8"))
    assert partial["completed"] == 2 and partial["remaining"] == 1

    async def finish(batch, base_url, concurrency):
        assert [case["id"] for case in batch] == [cases[2]["id"]]
        return [{"id": batch[0]["id"], "category": batch[0]["category"],
                 "passed": False, "reason": "evidence=False", "response": {}}]

    monkeypatch.setattr(evaluator, "evaluate_live", finish)
    final = await evaluator.evaluate_with_checkpoints(
        cases, "http://127.0.0.1:8000", report_path,
        concurrency=1, batch_size=2, resume=True)
    assert final["completed"] == 3 and final["remaining"] == 0
    assert final["summary"]["passed"] == 2


@pytest.mark.asyncio
async def test_resume_rejects_different_target(monkeypatch, tmp_path):
    cases = load_cases()[:1]
    path = tmp_path / "logistics_agent_eval_report_live_v5.json"
    evaluator._checkpoint(path, cases, {}, "http://127.0.0.1:8000")
    with pytest.raises(ValueError, match="不一致"):
        await evaluator.evaluate_with_checkpoints(
            cases, "http://other.example", path, concurrency=1, batch_size=1,
            resume=True)
