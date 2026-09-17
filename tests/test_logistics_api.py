def test_exception_classify_api(client):
    response = client.post("/api/logistics/exception-classify", json={
        "description": "包裹在清关，海关要求补资料",
    })
    assert response.status_code == 200
    assert response.json()["category"] == "清关补料"


def test_exception_classify_api_validates_description(client):
    response = client.post("/api/logistics/exception-classify", json={"description": ""})
    assert response.status_code == 422
