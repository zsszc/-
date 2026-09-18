import json
from pathlib import Path

from fastapi import APIRouter

from app.core.taxonomy import TOPIC_NAMES
from app.kb.sources import SOURCE_TYPES
from app.tools.business import list_user_shipments
from app.tools.registry import builtin_specs

router = APIRouter(prefix="/api/logistics", tags=["logistics"])
ROOT = Path(__file__).resolve().parents[2]


@router.get("/overview")
async def overview() -> dict:
    eval_path = ROOT / "data/evals/logistics_regression.jsonl"
    cases = [line for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()] if eval_path.exists() else []
    tools = [name for name in ("query_shipment", "assess_shipment_sla", "estimate_shipping_fee", "classify_logistics_exception", "check_prohibited_item") if any(s.name == name for s in builtin_specs())]
    shipments = list_user_shipments("demo-user")
    status_distribution = {}
    carrier_summary = {}
    exception_distribution = {}
    for shipment in shipments:
        status_distribution[shipment["status"]] = status_distribution.get(shipment["status"], 0) + 1
        carrier = shipment["carrier"]
        carrier_summary.setdefault(carrier, {"shipments": 0, "on_track": 0})
        carrier_summary[carrier]["shipments"] += 1
        if shipment["status"] in {"派送中", "已签收"}:
            carrier_summary[carrier]["on_track"] += 1
        if shipment.get("exception_code"):
            exception_distribution[shipment["exception_code"]] = exception_distribution.get(shipment["exception_code"], 0) + 1
    handoff_cases = sum(any(word in line for word in ("人工", "工单", "理赔")) for line in cases)
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
        "operations": {
            "shipment_total": len(shipments),
            "status_distribution": status_distribution,
            "exception_distribution": exception_distribution,
            "carrier_summary": carrier_summary,
            "human_handoff_rate": round(handoff_cases / len(cases), 3) if cases else 0,
        },
        "capabilities": tools,
    }
