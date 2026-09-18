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


def test_ticket_draft_api_returns_structured_missing_fields(client):
    response = client.post("/api/logistics/ticket-draft", json={"description": "包裹破损，需要理赔"})
    data = response.json()
    assert response.status_code == 200
    assert data["field_validation"]["complete"] is False
    assert "tracking_no" in data["field_validation"]["missing_fields"]


def test_ticket_draft_api_can_mark_damage_case_complete(client):
    response = client.post("/api/logistics/ticket-draft", json={
        "description": "包裹破损，需要理赔", "tracking_no": "CNDE20260917001",
        "contact_name": "张三", "contact_phone": "+8613800000000",
        "evidence_items": ["外包装照片", "签收记录"],
    })
    assert response.status_code == 200
    assert response.json()["field_validation"]["complete"] is True


def test_ticket_draft_api_validates_contact_phone(client):
    response = client.post("/api/logistics/ticket-draft", json={
        "description": "包裹破损", "contact_phone": "not-a-phone",
    })
    assert response.status_code == 422
