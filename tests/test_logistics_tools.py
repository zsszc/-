import pytest

from app.tools.business import owns_shipment, shipment_snapshot
from app.tools.builtin.logistics import (
    classify_logistics_exception, estimate_shipping_fee, query_shipment,
)


def test_shipment_snapshot_is_stable_and_has_operational_fields():
    first = shipment_snapshot("CNDE20260917001")
    assert first == shipment_snapshot("CNDE20260917001")
    assert {"tracking_no", "status", "current_node", "trace"} <= first.keys()


def test_shipment_snapshot_exposes_structured_timeline():
    snapshot = shipment_snapshot("CNDE20260917001")
    assert {"events", "route", "service_level", "sla_due_at", "exception_code"} <= snapshot.keys()
    assert {"origin", "destination"} <= snapshot.keys()
    assert len(snapshot["events"]) == 5
    assert {"event_id", "occurred_at", "location", "status", "description", "completed"} <= snapshot["events"][0].keys()
    assert sum(event["completed"] for event in snapshot["events"]) >= 1


def test_shipment_is_scoped_to_user_identity():
    assert owns_shipment("demo-user", "CNDE20260917001")
    assert not owns_shipment("", "CNDE20260917001")
    assert not owns_shipment("demo-user", "UNKNOWN")


@pytest.mark.asyncio
async def test_query_shipment_rejects_unknown_owner():
    result = await query_shipment.ainvoke({"tracking_no": "UNKNOWN", "user_id": "demo-user"})
    assert result["code"] == "shipment_not_owned"


@pytest.mark.asyncio
async def test_estimate_shipping_fee_is_explainable():
    result = await estimate_shipping_fee.ainvoke({
        "origin": "深圳", "destination": "德国", "weight_kg": 2,
        "transport_mode": "标准",
    })
    assert result["estimated_fee_cny"] == 151
    assert "最终报价" in result["notice"]


@pytest.mark.asyncio
async def test_classify_logistics_exception_returns_next_materials():
    result = await classify_logistics_exception.ainvoke({"description": "包裹在清关，海关要求补资料"})
    assert result["category"] == "清关补料"
    assert "收件人信息" in result["required_materials"]
