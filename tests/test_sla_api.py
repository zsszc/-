def test_sla_assessment_api(client):
    response = client.post("/api/logistics/sla-assessment", json={
        "tracking_no": "CNDE20260917001", "user_id": "demo-user",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "local-demo"
    assert data["standard_days"] == 10
    assert data["sla_status"] in {"待发运", "观察中", "临近完成", "已完成"}


def test_sla_assessment_hides_unknown_shipment(client):
    response = client.post("/api/logistics/sla-assessment", json={
        "tracking_no": "UNKNOWN", "user_id": "demo-user",
    })
    assert response.status_code == 404
