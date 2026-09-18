import json
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage

from app.graph import nodes


CASES = [json.loads(line) for line in (Path("data/evals/logistics_abstention.jsonl")).read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_logistics_out_of_scope_cases_take_abstention_path(monkeypatch):
    monkeypatch.setattr(nodes.query_understanding, "understand",
                        _aval({"standard": "库外物流问题", "expanded": []}))
    monkeypatch.setattr(nodes.retrieval, "search_knowledge", _aval([]))
    for case in CASES:
        out = await nodes.retrieve_knowledge({"messages": [HumanMessage(case["query"])]})
        assert case["must_abstain"] is True
        assert out["evidence_strong"] is False
        assert out["fallback_source"] == "retrieval_low_conf"
        assert out["retrieved_snapshot"] == []


@pytest.mark.asyncio
async def test_abstention_reply_offers_human_handoff(monkeypatch):
    inserted = []
    monkeypatch.setattr(nodes.repository, "insert_low_confidence", _capture(inserted))
    out = await nodes.fallback_reply({
        "messages": [HumanMessage(CASES[0]["query"])], "conversation_id": 7,
        "fallback_source": "retrieval_low_conf", "retrieved_snapshot": [],
        "evidence_confidence": 0.0, "trace": {},
    })
    assert out["suggested_actions"] == [{"type": "transfer_human"}]
    assert inserted and inserted[0][1]["retrieved_chunks"] == []


def _aval(value):
    async def _f(*args, **kwargs):
        return value
    return _f


def _capture(target):
    async def _f(*args, **kwargs):
        target.append((args, kwargs))
    return _f
