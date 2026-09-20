import logging
from typing import Literal

from pydantic import BaseModel, Field

from app.core import llm
from app.core.llm import get_chat_model
from app.core.prompts import INTENT_CLASSIFY_PROMPT, INTENT_JSON_PROMPT

logger = logging.getLogger(__name__)

INTENTS = ("运单查询", "清关咨询", "费用时效", "异常处理", "理赔", "禁限寄", "人工", "闲聊", "其他")


_FALLBACK_TERMS = {
    "运单查询": ("运单查询", "查运单", "物流轨迹", "物流状态", "包裹到哪"),
    "清关咨询": ("清关", "报关", "海关", "关税", "进口税"),
    "费用时效": ("运费", "报价", "计费重量", "运输时效", "运输费用"),
    "异常处理": ("派送失败", "地址填错", "物流异常", "退运", "包裹破损", "包裹丢失"),
    "理赔": ("理赔", "索赔", "赔偿"),
    "禁限寄": ("禁寄", "限寄", "能不能寄", "可不可以寄"),
    "人工": ("转人工", "人工客服", "找人工", "建工单", "创建工单"),
}


def _safe_fallback(query: str) -> dict:
    """只对单一明确物流意图降级；交叉诉求及库外问题仍归其他。"""
    matched = {intent for intent, terms in _FALLBACK_TERMS.items()
               if any(term in query for term in terms)}
    if "人工" in matched:
        return {"intent": "人工", "confidence": 0.55}
    if "理赔" in matched and matched <= {"理赔", "异常处理"}:
        return {"intent": "理赔", "confidence": 0.55}
    if len(matched) == 1:
        return {"intent": matched.pop(), "confidence": 0.55}
    return {"intent": "其他", "confidence": 0.0}


async def _classify_json(query: str, history: str) -> "_Intent":
    model = get_chat_model(streaming=False, slot="intent", thinking=False,
                           temperature=0).bind(response_format={"type": "json_object"})
    response = await (INTENT_JSON_PROMPT | model).ainvoke(
        {"query": query, "history": history or "(无)"})
    if not isinstance(response.content, str) or not response.content.strip():
        raise ValueError("JSON Output 未返回正文")
    return _Intent.model_validate_json(response.content)


class _Intent(BaseModel):
    intent: Literal["运单查询", "清关咨询", "费用时效", "异常处理", "理赔", "禁限寄", "人工", "闲聊", "其他"] = Field(
        description="九类意图之一")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="判断把握 0-1")


async def classify(query: str, history: str = "") -> dict:
    """工具调用优先；解析失败时仅意图槽位走受校验 JSON，最后保守词规则。"""
    try:
        model = llm.structured(_Intent, slot="intent")
        r: _Intent = await (INTENT_CLASSIFY_PROMPT | model).ainvoke(
            {"query": query, "history": history or "(无)"})
    except Exception as exc:
        logger.warning("意图工具调用失败(%s)，尝试 JSON Output", type(exc).__name__)
        try:
            r = await _classify_json(query, history)
        except Exception as json_exc:
            logger.warning("意图 JSON Output 失败(%s)，使用保守路由", type(json_exc).__name__)
            return _safe_fallback(query)
    intent = r.intent if r.intent in INTENTS else "其他"
    return {"intent": intent, "confidence": float(r.confidence)}
