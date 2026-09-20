"""当前物流 RAG 评估 API：只读取传统检索与行为评测产物。"""

import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import rageval

REPORT = {
    "meta": {"samples": 30, "single_samples": 19, "multi_samples": 11,
             "relevant_sections": 19, "top_k": 5, "generated_at": "2026-09-18T23:30:00+08:00"},
    "strategies": {
        "vector": {"overall": {"recall_at_5": 0.9, "mrr_at_5": 0.8, "ndcg_at_5": 0.82},
                   "by_kind": {}, "errors": 0},
        "hybrid_rerank": {"overall": {"recall_at_5": 0.96, "mrr_at_5": 0.91, "ndcg_at_5": 0.94},
                          "by_kind": {}, "errors": 0},
    },
    "results": {},
}


@pytest.fixture
def app():
    instance = FastAPI()
    instance.include_router(rageval.router)
    return instance


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


@pytest.fixture
def reports(tmp_path, monkeypatch):
    retrieval = tmp_path / "logistics_retrieval_eval_report.json"
    behavior = tmp_path / "logistics_agent_eval_report_live.json"
    monkeypatch.setattr(rageval, "RETRIEVAL_REPORT", retrieval)
    monkeypatch.setattr(rageval, "BEHAVIOR_REPORT", behavior)
    return retrieval, behavior


async def test_missing_report_is_a_state_not_an_error(client, reports):
    body = (await client.get("/api/rag-eval/overview")).json()
    assert body["present"] is False
    assert body["make"] == "make eval-logistics-retrieval"
    assert body["job"]["artifacts"]["json"]["present"] is False


async def test_overview_reads_retrieval_and_behavior_artifacts(client, reports):
    retrieval, behavior = reports
    retrieval.write_text(json.dumps(REPORT, ensure_ascii=False), encoding="utf-8")
    behavior.write_text(json.dumps({"summary": {"total": 30, "passed": 28, "pass_rate": 0.9333}}),
                        encoding="utf-8")
    body = (await client.get("/api/rag-eval/overview")).json()
    assert body["present"] is True
    assert body["retrieval"] == REPORT["strategies"]
    assert body["meta"]["samples"] == 30
    assert body["behavior"]["passed"] == 28
    assert body["job"]["artifacts"]["json"]["present"] is True


async def test_best_strategy_uses_ndcg_then_mrr(client, reports):
    retrieval, _ = reports
    retrieval.write_text(json.dumps(REPORT, ensure_ascii=False), encoding="utf-8")
    body = (await client.get("/api/rag-eval/overview")).json()
    assert body["best"] == {"strategy": "hybrid_rerank", "ndcg_at_5": 0.94, "mrr_at_5": 0.91}


async def test_broken_report_reads_as_missing(client, reports):
    retrieval, _ = reports
    retrieval.write_text("{半个 json", encoding="utf-8")
    assert (await client.get("/api/rag-eval/overview")).json()["present"] is False
