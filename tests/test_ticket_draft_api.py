def test_ticket_draft_api_reuses_exception_classification(client):
    response = client.post("/api/logistics/ticket-draft", json={
        "description": "德国清关要求补资料", "tracking_no": "CNDE20260917001",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "清关补料"
    assert "CNDE20260917001" in data["title"]
    assert data["requires_confirmation"] is True
    assert "收件人信息" in data["required_materials"]


def test_ticket_draft_api_validates_input(client):
    assert client.post("/api/logistics/ticket-draft", json={"description": ""}).status_code == 422
    assert client.post("/api/logistics/ticket-draft", json={"description": "异常", "tracking_no": "x" * 101}).status_code == 422
