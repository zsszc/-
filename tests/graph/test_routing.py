import pytest
from langchain_core.messages import AIMessage

from app.config import settings
from app.core.intent import INTENTS
from app.core.prompts import SCRIPT_REPLY_OTHER
from app.graph.routing import (
    confidence_gate, route_by_intent, should_continue, INTENT_TO_ROUTE,
)


@pytest.mark.parametrize("intent,expect", [
    ("投诉", "escalate"),
    ("闲聊", "fallback_script"),
    ("其他", "fallback_script"),
    ("清关咨询", "knowledge"),
    ("理赔", "knowledge"),
    ("禁限寄", "knowledge"),
    ("费用时效", "business"),
    ("运单查询", "business"),
    ("售后", "refund_flow"),
    ("人工", "business"),
    ("物流", "business"),
    ("订单", "business"),
])
def test_route_by_intent_five_outlets(intent, expect):
    assert route_by_intent({"intent": intent}) == expect


def test_route_by_intent_unknown_defaults_business():
    assert route_by_intent({"intent": "火星语"}) == "business"
    assert route_by_intent({}) == "business"


def test_account_scope_faq_goes_to_knowledge_not_tracking_tool():
    assert route_by_intent({"intent": "运单查询", "resolved_query": "登录后能查看哪些运单，请按步骤说明"}) == "knowledge"
    assert route_by_intent({"intent": "其他", "resolved_query": "登录后查看运单的权限范围是什么"}) == "knowledge"
    assert route_by_intent({"intent": "运单查询", "resolved_query": "查询运单号 SF123456789 的状态"}) == "business"


@pytest.mark.parametrize("query", [
    "锂电池可以寄到美国吗", "汽油能不能走国际快递",
    "粉末类物品能否寄运", "锂电池走特快到美国，费用和禁寄风险分别是什么",
])
def test_specific_item_precheck_reaches_business_tools(query):
    assert route_by_intent({"intent": "禁限寄", "resolved_query": query}) == "business"


def test_general_prohibited_policy_keeps_knowledge_gate():
    assert route_by_intent({"intent": "禁限寄", "resolved_query": "国际禁限寄政策是什么"}) == "knowledge"


def test_unspecified_other_reply_does_not_imply_verified_answer():
    assert "无法确认" in SCRIPT_REPLY_OTHER
    assert "请补充" in SCRIPT_REPLY_OTHER


def test_intent_to_route_covers_nine_classes():
    assert set(INTENTS) <= set(INTENT_TO_ROUTE)


def test_confidence_gate():
    assert confidence_gate({"evidence_strong": True}) == "strong"
    assert confidence_gate({"evidence_strong": False}) == "weak"
    assert confidence_gate({}) == "weak"


def test_should_continue_stops_when_no_tool_calls():
    state = {"messages": [AIMessage("答完了")], "steps": 1, "tokens_used": 0}
    assert should_continue(state) == "stop"


def test_should_continue_continues_on_tool_calls():
    ai = AIMessage("", tool_calls=[{"name": "query_order", "args": {}, "id": "1"}])
    state = {"messages": [ai], "steps": 1, "tokens_used": 0}
    assert should_continue(state) == "continue"


def test_should_continue_stops_on_step_cap():
    ai = AIMessage("", tool_calls=[{"name": "query_order", "args": {}, "id": "1"}])
    state = {"messages": [ai], "steps": settings.max_agent_steps, "tokens_used": 0}
    assert should_continue(state) == "stop"


def test_token_花销不再当停止条件():
    # 环里只按步数封顶。token 记账继续走(进 trace、给 ch09 统计),但不参与判断:
    # 混在这里卡,阈值估偏一次就把整条工具链掐断,而且掐在模型已经决定调工具之后
    ai = AIMessage("", tool_calls=[{"name": "query_order", "args": {}, "id": "1"}])
    state = {"messages": [ai], "steps": 1, "tokens_used": 10_000_000}
    assert should_continue(state) == "continue"
