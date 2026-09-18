"""跨境物流关键链路的 API 层端到端冒烟验收。"""


def test_logistics_business_journey(client):
    shipment = client.post("/api/logistics/shipment-query", json={
        "tracking_no": "CNDE20260917001", "user_id": "demo-user",
    })
    assert shipment.status_code == 200
    assert shipment.json()["events"]

    sla = client.post("/api/logistics/sla-assessment", json={
        "tracking_no": "CNDE20260917001", "user_id": "demo-user",
    })
    assert sla.status_code == 200
    assert sla.json()["standard_days"] == 10

    fee = client.post("/api/logistics/shipping-fee", json={
        "origin": "中国", "destination": "德国", "weight_kg": 2, "transport_mode": "标准",
    })
    assert fee.status_code == 200
    assert fee.json()["estimated_fee_cny"] > 0

    item = client.post("/api/logistics/prohibited-item-check", json={"item_name": "锂电池"})
    assert item.status_code == 200
    assert item.json()["decision"] == "requires_review"

    exception = client.post("/api/logistics/exception-classify", json={"description": "德国清关要求补资料"})
    assert exception.status_code == 200
    assert exception.json()["category"] == "清关补料"

    ticket = client.post("/api/logistics/ticket-draft", json={
        "description": "包裹破损，需要理赔", "tracking_no": "CNDE20260917001",
    })
    assert ticket.status_code == 200
    assert ticket.json()["requires_confirmation"] is True


def test_logistics_business_journey_enforces_boundaries(client):
    unknown = client.post("/api/logistics/shipment-query", json={
        "tracking_no": "UNKNOWN", "user_id": "demo-user",
    })
    assert unknown.status_code == 404

    invalid_fee = client.post("/api/logistics/shipping-fee", json={
        "origin": "中国", "destination": "德国", "weight_kg": 0, "transport_mode": "标准",
    })
    assert invalid_fee.status_code == 422
