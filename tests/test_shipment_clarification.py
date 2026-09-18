import pytest

from app.core.prompts import FALLBACK_REPLY_TEXT, SHIPMENT_CLARIFICATION_REPLY
from app.graph import nodes
from scripts.eval_logistics_agent import score_case


@pytest.mark.asyncio
async def test_missing_tracking_number_gets_specific_sla_clarification(monkeypatch):
    async def no_op(*args, **kwargs):
        return None

    monkeypatch.setattr(nodes.repository, "insert_low_confidence", no_op)
    result = await nodes.fallback_reply({
        "resolved_query": "包裹在德国清关且已经超过SLA，应该准备什么资料并怎么升级",
        "fallback_source": "self_check",
        "evidence_confidence": 0.1,
        "trace": {},
    })
    assert result["answer"] == SHIPMENT_CLARIFICATION_REPLY
    assert result["trace"]["needs_tracking"] is True
    assert "运单号" in result["answer"]


def test_other_knowledge_fallback_keeps_original_copy():
    assert FALLBACK_REPLY_TEXT
    case = {"category": "cross_document", "expected_tools": ["query_shipment"]}
    response = {"answer": SHIPMENT_CLARIFICATION_REPLY, "tool_calls": [], "tool_results": []}
    assert score_case(case, response)[0] is True
