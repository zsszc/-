from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool
from pydantic import Field

from app.tools import registry
from app.tools.business import owns_shipment, shipment_snapshot


@tool
async def query_shipment(
    tracking_no: Annotated[str, Field(description="国际运单号，例如 CNDE20260917001")],
    user_id: Annotated[str, InjectedToolArg],
) -> dict:
    """查询当前用户国际运单的状态、节点、承运商和最近轨迹。"""
    if not owns_shipment(user_id, tracking_no):
        return {"error": "没有找到您的这票运单", "code": "shipment_not_owned"}
    return shipment_snapshot(tracking_no)


@tool
async def estimate_shipping_fee(
    origin: Annotated[str, Field(description="始发地国家或城市")],
    destination: Annotated[str, Field(description="目的地国家或城市")],
    weight_kg: Annotated[float, Field(gt=0, le=1000, description="包裹重量，单位 kg")],
    transport_mode: Annotated[str, Field(description="运输方式：经济、标准或特快")],
) -> dict:
    """根据基础参数估算跨境运输费用，仅用于方案比较，不代表最终报价。"""
    multipliers = {"经济": 38, "标准": 58, "特快": 96}
    multiplier = multipliers.get(transport_mode, 58)
    fee = round(max(weight_kg, 0.5) * multiplier + 35, 2)
    return {
        "origin": origin, "destination": destination, "weight_kg": weight_kg,
        "transport_mode": transport_mode, "estimated_fee_cny": fee,
        "notice": "估算不含目的国税费、偏远地区费和特殊处理费，以承运商最终报价为准",
    }


@tool
async def classify_logistics_exception(
    description: Annotated[str, Field(description="用户描述的物流异常现象")],
) -> dict:
    """将物流异常归类并给出下一步资料建议，供人工工单和运营统计使用。"""
    text = description.lower()
    rules = (
        (("清关", "海关", "补资料", "查验"), "清关补料", "运单号、收件人信息、承运商通知截图"),
        (("破损", "碎了", "少件"), "包裹破损或少件", "运单号、外包装和内件照片、签收记录"),
        (("丢了", "丢失", "找不到"), "疑似丢失", "运单号、寄件凭证、商品价值证明"),
        (("地址", "改址", "电话错误"), "收件信息问题", "运单号、正确收件信息、收件人联系方式"),
        (("派送失败", "没人接", "联系不上"), "派送异常", "运单号、可联系时间、备用联系方式"),
        (("延误", "没更新", "不动了", "晚到"), "运输延误", "运单号、承诺时效、最近轨迹截图"),
    )
    for keywords, category, materials in rules:
        if any(keyword in text for keyword in keywords):
            return {"category": category, "severity": "medium", "required_materials": materials}
    return {"category": "其他异常", "severity": "low", "required_materials": "运单号和完整异常描述"}


registry.register(registry.spec_from_langchain_tool(query_shipment, source="builtin", inject_user_id=True))
registry.register(registry.spec_from_langchain_tool(estimate_shipping_fee, source="builtin"))
registry.register(registry.spec_from_langchain_tool(classify_logistics_exception, source="builtin"))
