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


registry.register(registry.spec_from_langchain_tool(query_shipment, source="builtin", inject_user_id=True))
registry.register(registry.spec_from_langchain_tool(estimate_shipping_fee, source="builtin"))
