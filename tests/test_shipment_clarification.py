import pytest

from app.core.prompts import (
    FALLBACK_REPLY_TEXT, SHIPMENT_CLARIFICATION_REPLY,
    SHIPMENT_CONTEXT_CLARIFICATION_REPLY,
)
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


@pytest.mark.asyncio
@pytest.mark.parametrize("query", [
    "运单显示派送失败，能否改地址以及是否会产生费用",
    "清关失败被退运，退运费用由谁承担，下一步如何申请",
])
async def test_missing_tracking_in_cross_document_asks_for_number(monkeypatch, query):
    async def no_op(*args, **kwargs):
        return None

    monkeypatch.setattr(nodes.repository, "insert_low_confidence", no_op)
    result = await nodes.fallback_reply({
        "resolved_query": query, "fallback_source": "self_check",
        "evidence_confidence": 0.1, "trace": {},
    })
    assert result["answer"] == SHIPMENT_CONTEXT_CLARIFICATION_REPLY
    assert result["trace"]["needs_tracking"] is True
    assert "运单号" in result["answer"]


@pytest.mark.asyncio
async def test_known_tracking_number_does_not_ask_for_it_again(monkeypatch):
    async def no_op(*args, **kwargs):
        return None

    monkeypatch.setattr(nodes.repository, "insert_low_confidence", no_op)
    result = await nodes.fallback_reply({
        "resolved_query": "运单 CNDE20260917001 显示派送失败，怎么改地址",
        "fallback_source": "retrieval_low_conf", "trace": {},
    })
    assert result["trace"]["needs_tracking"] is False
