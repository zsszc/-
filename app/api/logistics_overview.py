import json
from pathlib import Path

from fastapi import APIRouter

from app.core.taxonomy import TOPIC_NAMES
from app.kb.sources import SOURCE_TYPES
from app.tools.registry import builtin_specs

router = APIRouter(prefix="/api/logistics", tags=["logistics"])
ROOT = Path(__file__).resolve().parents[2]


@router.get("/overview")
async def overview() -> dict:
    eval_path = ROOT / "data/evals/logistics_regression.jsonl"
    cases = [line for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()] if eval_path.exists() else []
    tools = [name for name in ("query_shipment", "assess_shipment_sla", "estimate_shipping_fee", "classify_logistics_exception", "check_prohibited_item") if any(s.name == name for s in builtin_specs())]
    milvus = {"status": "unavailable", "count": None}
    try:
        from app.kb import milvus_client
        client = milvus_client.get_client()
        milvus = {"status": "ready", "count": milvus_client.count(client)}
    except Exception:
        pass
    return {
        "scope": "local-demo",
        "metrics": {
            "knowledge_sources": len(SOURCE_TYPES),
            "regression_cases": len(cases),
            "logistics_topics": len(TOPIC_NAMES),
            "registered_tools": len(tools),
            "milvus": milvus,
        },
        "capabilities": tools,
    }
