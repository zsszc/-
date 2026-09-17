def test_logistics_overview_api(client):
    response = client.get("/api/logistics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "local-demo"
    assert data["metrics"]["knowledge_sources"] == 6
    assert data["metrics"]["regression_cases"] >= 12
    assert data["metrics"]["logistics_topics"] == 17
    assert "query_shipment" in data["capabilities"]
