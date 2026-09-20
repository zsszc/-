import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.core import intent
from app.core.intent import _safe_fallback


class _JSONModel:
    def __init__(self, content: str):
        self.content = content

    def bind(self, **kwargs):
        assert kwargs["response_format"] == {"type": "json_object"}
        return RunnableLambda(lambda _: AIMessage(content=self.content))


def test_clear_customs_question_uses_safe_fallback():
    assert _safe_fallback("德国个人件清关需要哪些资料？") == {
        "intent": "清关咨询", "confidence": 0.55,
    }
    assert _safe_fallback("出口报关要准备什么？")["intent"] == "清关咨询"


def test_unknown_question_remains_other():
    assert _safe_fallback("明天天气如何？") == {"intent": "其他", "confidence": 0.0}


@pytest.mark.parametrize(("query", "expected"), [
    ("帮我查运单查询", "运单查询"),
    ("国际运费怎么算", "费用时效"),
    ("派送失败怎么办", "异常处理"),
    ("包裹破损如何理赔", "理赔"),
    ("锂电池能不能寄", "禁限寄"),
    ("请帮我转人工", "人工"),
])
def test_clear_logistics_question_uses_narrow_rule(query, expected):
    assert _safe_fallback(query)["intent"] == expected


def test_conflicting_or_out_of_scope_question_stays_other():
    assert _safe_fallback("德国清关和运费一起怎么算") == {"intent": "其他", "confidence": 0.0}
    assert _safe_fallback("帮我写首诗") == {"intent": "其他", "confidence": 0.0}


@pytest.mark.asyncio
async def test_json_fallback_validates_enum_when_tool_call_fails(monkeypatch):
    async def broken_tool(_):
        raise ValueError("bad tool arguments")

    monkeypatch.setattr(intent.llm, "structured", lambda *a, **k: RunnableLambda(broken_tool))
    monkeypatch.setattr(intent, "get_chat_model", lambda **k: _JSONModel(
        '{"intent":"禁限寄","confidence":0.9}'))
    assert await intent.classify("锂电池能寄吗") == {"intent": "禁限寄", "confidence": 0.9}


@pytest.mark.asyncio
async def test_invalid_json_cannot_force_unrecognized_intent(monkeypatch):
    async def broken_tool(_):
        raise ValueError("bad tool arguments")

    monkeypatch.setattr(intent.llm, "structured", lambda *a, **k: RunnableLambda(broken_tool))
    monkeypatch.setattr(intent, "get_chat_model", lambda **k: _JSONModel(
        '{"intent":"凭空编造","confidence":0.9}'))
    assert await intent.classify("明天天气如何") == {"intent": "其他", "confidence": 0.0}
