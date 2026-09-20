"""物流 Agent 综合评测产物的只读汇总。"""

import json
from collections import Counter
from pathlib import Path

from fastapi import APIRouter

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/evals/logistics_agent_eval.jsonl"
LIVE_REPORT = ROOT / "data/evals/logistics_agent_eval_report_live_v5.json"
EXPECTED_COUNTS = {
    "policy_process": 100,
    "cross_document": 70,
    "tool_operation": 60,
    "out_of_scope": 50,
    "boundary_clarification": 20,
}
router = APIRouter(prefix="/api/agent-eval")


def _dataset_overview() -> dict:
    if not DATASET.exists():
        return {"status": "missing", "total": 0, "categories": {}, "must_abstain": 0, "requires_citations": 0}
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    categories = dict(Counter(row.get("category") for row in rows))
    return {
        "status": "ok" if len(rows) == 300 and categories == EXPECTED_COUNTS else "attention",
        "total": len(rows), "categories": categories,
        "must_abstain": sum(bool(row.get("must_abstain")) for row in rows),
        "requires_citations": sum(bool(row.get("requires_citations")) for row in rows),
    }


def _live_overview() -> dict:
    if not LIVE_REPORT.exists():
        return {"status": "missing", "summary": None, "by_category": {}}
    try:
        report = json.loads(LIVE_REPORT.read_text(encoding="utf-8"))
        summary = report.get("summary") or {}
        completed = report.get("completed", summary.get("total", 0))
        target_total = report.get("target_total", completed)
        return {"status": "ok" if completed >= target_total else "partial",
                "completed": completed, "target_total": target_total,
                "summary": {k: summary.get(k) for k in ("total", "passed", "pass_rate")},
                "by_category": summary.get("by_category", {}), "base_url": report.get("base_url")}
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "error", "summary": None, "by_category": {}, "note": f"{type(exc).__name__}: {exc}"}


def build_overview() -> dict:
    return {"dataset": _dataset_overview(), "live": _live_overview(),
            "commands": {"offline": ".venv/bin/python scripts/eval_logistics_agent.py --offline",
                         "sample": ".venv/bin/python scripts/eval_logistics_agent.py --live --limit 5",
                         "full": ".venv/bin/python scripts/eval_logistics_agent.py --live --limit 300 --resume"}}


@router.get("/overview")
async def overview() -> dict:
    return build_overview()
