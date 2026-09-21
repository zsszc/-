from app.kb.documents import build_chunks
from app.kb.sources import KB_DIR, SOURCE_TYPES


def test_curated_service_playbook_is_registered_and_chunkable():
    assert SOURCE_TYPES["service-playbook.md"] == "manual"
    text = (KB_DIR / "service-playbook.md").read_text(encoding="utf-8")
    chunks = build_chunks(text, content_type="manual")
    questions = {chunk.questions for chunk in chunks}
    assert {
        "派送失败后怎么重新安排？",
        "收件电话或地址写错了能修改吗？",
        "商业发票应该填写哪些内容？",
        "登录后能查看哪些运单？",
        "DHL 和 UPS 哪个更适合当前线路？",
    } <= questions
    assert all(chunk.answer.strip() for chunk in chunks)
    assert all(chunk.content_type == "manual" for chunk in chunks)
    assert "https://www.ups.com/us/en/track/change-delivery" in text
    assert "https://www.dhl.com/" in text
    assert "不应把这层校验宣称为生产级权限控制" in text
