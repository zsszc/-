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
