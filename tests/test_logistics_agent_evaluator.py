from collections import Counter

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
