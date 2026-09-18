from app.api import agent_eval
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def test_agent_eval_overview_reads_dataset_without_live_report(monkeypatch, tmp_path):
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text("\n".join(
        '{"category": "policy_process", "must_abstain": false, "requires_citations": true}'
        for _ in range(300)
    ) + "\n", encoding="utf-8")
    monkeypatch.setattr(agent_eval, "DATASET", dataset)
    monkeypatch.setattr(agent_eval, "LIVE_REPORT", tmp_path / "missing.json")
    result = agent_eval.build_overview()
    assert result["dataset"]["total"] == 300
    assert result["dataset"]["status"] == "attention"
    assert result["live"]["status"] == "missing"
    assert "--limit 5" in result["commands"]["sample"]


async def test_agent_eval_api_exposes_read_only_overview():
    app = FastAPI()
    app.include_router(agent_eval.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/agent-eval/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["dataset"]["total"] == 300
    assert body["dataset"]["categories"]["out_of_scope"] == 50
