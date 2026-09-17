def test_prohibited_item_check_api(client):
    for item, decision in (("汽油", "prohibited"), ("锂电池", "requires_review"), ("棉衣", "可咨询寄运")):
        response = client.post("/api/logistics/prohibited-item-check", json={"item_name": item})
        assert response.status_code == 200
        assert response.json()["decision"] == decision


def test_prohibited_item_check_api_validates_length(client):
    assert client.post("/api/logistics/prohibited-item-check", json={"item_name": ""}).status_code == 422
