import pytest

from app.core.prompts import SCRIPT_REPLY_OUT_OF_SCOPE
from app.graph import nodes
from app.graph.routing import INTENT_TO_ROUTE, route_by_intent


def test_fee_questions_enter_agent_tool_route():
    assert INTENT_TO_ROUTE["费用时效"] == "business"
    assert route_by_intent({"intent": "费用时效"}) == "business"


@pytest.mark.asyncio
async def test_explicit_out_of_scope_question_is_refused():
    result = await nodes.script_reply({
        "intent": "其他",
        "resolved_query": "明天深圳飞法兰克福的航班是否会取消",
    })
    assert result["answer"] == SCRIPT_REPLY_OUT_OF_SCOPE
    assert result["trace"]["out_of_scope"] is True
    assert "无法确认" in result["answer"]


def test_successful_tool_result_counts_as_evidence():
    from scripts.eval_logistics_agent import score_case

    case = {"category": "cross_document", "requires_citations": True}
    response = {"answer": "预计费用见下方拆解。", "tool_calls": [{"name": "estimate_shipping_fee"}],
                "tool_results": [{"name": "estimate_shipping_fee", "ok": True, "content": "transport_total_cny=200"}]}
    assert score_case(case, response)[0] is True
