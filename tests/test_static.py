from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_serves_chat_page():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    # 页面自包含且对接 /api/chat 的 SSE
    assert "/api/chat" in resp.text
    assert "session_id" in resp.text
    # 聊天页是客户看的页面,不留后台入口;后台各页自己带「聊天页 →」
    assert 'href="/admin"' not in resp.text


def test_admin_pages_are_reachable():
    """后台各页都能直接开;共享外壳(样式 + 脚本 + 导航)也在静态目录里。"""
    for path, marker in (
        ("/admin", "/api/admin/overview"),
        ("/kb", "/api/kb/overview"),
        ("/rag-eval", "/api/rag-eval/overview"),
        ("/review", "/api/review/queue"),
        ("/topics", "/api/topics/distribution"),
        ("/topics/questions", "/api/topics/questions"),
        ("/agent-eval", "/api/agent-eval/overview"),
        ("/observability", "/api/observability/overview"),
    ):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert marker in resp.text, path
        assert "/static/admin.js" in resp.text, path    # 后台导航一份共用
    for asset in ("/static/admin.js", "/static/admin-shell.css", "/static/acceptance.js", "/static/acceptance.css"):
        assert client.get(asset).status_code == 200, asset


def test_observability_page_labels_logistics_retrieval_metrics():
    page = client.get("/observability").text
    assert "物流检索趋势" in page
    assert "MRR@5" in page and "NDCG@5" in page
    assert "忠实度和库外拒答不在这一轮评估内" in page


def test_legacy_experiment_pages_redirect_to_agent_eval():
    for path in ("/acceptance", "/acceptance/eval", "/acceptance/data", "/acceptance/errors"):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 307
        assert resp.headers["location"] == "/agent-eval"


def test_shipment_detail_page_is_reachable():
    resp = client.get("/shipment-detail")
    assert resp.status_code == 200
    assert "运单详情" in resp.text
    assert "/api/logistics/shipment-query" in resp.text
    assert "events" in resp.text
