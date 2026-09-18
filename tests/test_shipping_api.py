def test_shipping_fee_api(client):
    response = client.post("/api/logistics/shipping-fee", json={
        "origin": "深圳", "destination": "德国", "weight_kg": 2, "transport_mode": "标准",
    })
    assert response.status_code == 200
    assert response.json()["estimated_fee_cny"] == 151
    assert "最终报价" in response.json()["notice"]


def test_shipping_fee_api_validates_mode_and_weight(client):
    for payload in (
        {"origin": "深圳", "destination": "德国", "weight_kg": 0, "transport_mode": "标准"},
        {"origin": "深圳", "destination": "德国", "weight_kg": 2, "transport_mode": "海运"},
    ):
        assert client.post("/api/logistics/shipping-fee", json=payload).status_code == 422


def test_shipping_fee_api_breaks_down_cost_and_tax_hint(client):
    response = client.post("/api/logistics/shipping-fee", json={
        "origin": "深圳", "destination": "德国", "weight_kg": 2,
        "transport_mode": "标准", "declared_value_cny": 1000,
    })
    data = response.json()
    assert response.status_code == 200
    assert data["fee_breakdown"]["transport_total_cny"] > data["estimated_fee_cny"]
    assert data["tax_estimate"]["duty_cny"] == 60
    assert data["tax_estimate"]["vat_cny"] == 201.4


def test_shipping_fee_api_without_declared_value_does_not_claim_tax_free(client):
    data = client.post("/api/logistics/shipping-fee", json={
        "origin": "深圳", "destination": "德国", "weight_kg": 2, "transport_mode": "标准",
    }).json()
    assert data["tax_estimate"]["tax_total_cny"] == 0
    assert "不代表海关最终征税" in data["notice"]
