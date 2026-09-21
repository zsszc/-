from langchain_core.messages import AIMessage

from app.config import settings

# 九类意图 → 五出口(写死的分流规则,spec §3.1 / README route_by_intent;
# 返回值 = build.py 条件边映射键,单一来源不漂移)
INTENT_TO_ROUTE: dict[str, str] = {
    "投诉": "escalate",
    "闲聊": "fallback_script",
    "其他": "fallback_script",
    "清关咨询": "knowledge",
    # 费用问题经常同时包含目的地、重量、运输方式和申报价值;
    # 先走 Agent 工具链才能一次完成运费拆解与税费估算,不能被知识库闸门提前兜底。
    "费用时效": "business",
    "异常处理": "knowledge",
    "理赔": "knowledge",
    "禁限寄": "knowledge",
    "售后": "refund_flow",
    "人工": "business",   # ch08:明确要求建工单/转人工 → 主力 Agent 走 create_ticket 确认流
    "运单查询": "business",
    "订单": "business",
}

_ITEM_PRECHECK_TERMS = (
    "能不能寄", "可以寄", "能否寄", "可不可以寄", "寄到", "寄运",
    "国际快递", "禁寄风险", "限寄风险",
)


def intent_route(intent: str, query: str = "") -> str:
    """明确物品寄运预检走工具；一般禁限寄政策仍走知识证据闸。"""
    # “登录后能查看哪些运单”问的是演示系统的权限说明，不是查询某个单号。
    # 意图模型容易把“运单”误判成运单查询，故只对这一窄问法强制走有引用的知识路。
    if "运单" in query and "登录" in query and ("哪些" in query or "权限" in query or "范围" in query):
        return "knowledge"
    if intent == "禁限寄" and any(term in query for term in _ITEM_PRECHECK_TERMS):
        return "business"
    return INTENT_TO_ROUTE.get(intent, "business")


def route_by_intent(state) -> str:
    """按意图分流;未知意图保守归 business(让 Agent 自己应对)。"""
    return intent_route(state.get("intent", ""), state.get("resolved_query", ""))


def confidence_gate(state) -> str:
    """知识路生成前证据闸:强放行、弱兜底。"""
    return "strong" if state.get("evidence_strong") else "weak"


def should_continue(state) -> str:
    """ReAct 停止条件:无 tool_calls 就收敛,步数封顶则强停,否则继续。

    只用步数封顶,不在这里卡 token。防打转靠的是步数:一步一次模型调用,数得清、好解释,
    各家 Agent SDK 给的也是 max_turns / max_iterations 这类步数上限。
    token 花销是另一件事——它管的是烧钱和撑爆上下文,不是死循环,阈值要按真实用量分布标定,
    归第 9 章的成本控制一起讲。混在这里卡,一次估偏就把工具链整条掐断,而且掐在模型
    已经决定调工具之后,用户只看到半句「我这就去查」。"""
    last = state["messages"][-1]
    has_tool_calls = isinstance(last, AIMessage) and bool(last.tool_calls)
    if not has_tool_calls:
        return "stop"
    if state.get("steps", 0) >= settings.max_agent_steps:
        return "stop"
    return "continue"
