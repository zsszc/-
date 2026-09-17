def test_shipment_query_api(client):
    response = client.post("/api/logistics/shipment-query", json={
        "tracking_no": "CNDE20260917001", "user_id": "demo-user",
    })
    assert response.status_code == 200
    assert response.json()["tracking_no"] == "CNDE20260917001"
    assert {"status", "current_node", "carrier", "trace"} <= response.json().keys()


def test_shipment_query_api_hides_unknown_shipment(client):
    response = client.post("/api/logistics/shipment-query", json={
        "tracking_no": "UNKNOWN", "user_id": "demo-user",
    })
    assert response.status_code == 404


def test_shipment_query_api_validates_identity(client):
    response = client.post("/api/logistics/shipment-query", json={
        "tracking_no": "CNDE20260917001", "user_id": "",
    })
    assert response.status_code == 422
