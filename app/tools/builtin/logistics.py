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
async def assess_shipment_sla(
    tracking_no: Annotated[str, Field(description="国际运单号，例如 CNDE20260917001")],
    user_id: Annotated[str, InjectedToolArg],
) -> dict:
    """基于演示运单状态评估 SLA，结果仅用于本地运营演示。"""
    snapshot = await query_shipment.ainvoke({"tracking_no": tracking_no, "user_id": user_id})
    if snapshot.get("code") == "shipment_not_owned":
        return snapshot
    state = snapshot["status"]
    states = {
        "已揽收": ("待发运", "等待始发地交运"),
        "运输中": ("观察中", "关注下一国际运输节点"),
        "清关中": ("观察中", "核对海关通知并准备补充资料"),
        "派送中": ("临近完成", "保持收件电话畅通"),
        "已签收": ("已完成", "如有破损或少件请及时保留凭证"),
    }
    sla_status, next_action = states.get(state, ("待确认", "联系人工核对运单状态"))
    return {"tracking_no": tracking_no, "carrier": snapshot["carrier"], "status": state,
            "standard_days": 10, "sla_status": sla_status, "next_action": next_action,
            "scope": "local-demo"}


@tool
async def estimate_shipping_fee(
    origin: Annotated[str, Field(description="始发地国家或城市")],
    destination: Annotated[str, Field(description="目的地国家或城市")],
    weight_kg: Annotated[float, Field(gt=0, le=1000, description="包裹重量，单位 kg")],
    transport_mode: Annotated[str, Field(description="运输方式：经济、标准或特快")],
    declared_value_cny: Annotated[float, Field(ge=0, le=1000000, description="申报价值，单位人民币；未知时填 0")]=0,
) -> dict:
    """根据基础参数估算运输费用并提示目的国税费，仅用于方案比较，不代表最终报价。"""
    multipliers = {"经济": 38, "标准": 58, "特快": 96}
    multiplier = multipliers.get(transport_mode, 58)
    base_fee = round(max(weight_kg, 0.5) * multiplier + 35, 2)
    fuel_surcharge = round(base_fee * 0.08, 2)
    remote_area_fee = 20 if any(word in destination for word in ("偏远", "岛", "Alaska", "Hawaii")) else 0
    transport_total = round(base_fee + fuel_surcharge + remote_area_fee, 2)
    if any(word in destination for word in ("德国", "法国", "意大利", "西班牙", "欧盟")):
        duty_rate, vat_rate = 0.06, 0.19
    elif any(word in destination for word in ("美国", "加拿大")):
        duty_rate, vat_rate = 0.05, 0.0
    else:
        duty_rate, vat_rate = 0.08, 0.13
    duty = round(declared_value_cny * duty_rate, 2)
    vat = round((declared_value_cny + duty) * vat_rate, 2)
    return {
        "origin": origin, "destination": destination, "weight_kg": weight_kg,
        "transport_mode": transport_mode, "estimated_fee_cny": base_fee,
        "fee_breakdown": {"base_fee_cny": base_fee, "fuel_surcharge_cny": fuel_surcharge,
                          "remote_area_fee_cny": remote_area_fee, "transport_total_cny": transport_total},
        "tax_estimate": {"declared_value_cny": declared_value_cny, "duty_rate": duty_rate,
                          "duty_cny": duty, "vat_rate": vat_rate, "vat_cny": vat,
                          "tax_total_cny": round(duty + vat, 2)},
        "notice": "税费仅按申报价值和目的地常见规则粗略估算，不代表海关最终征税；运输报价以承运商最终报价为准",
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


@tool
async def check_prohibited_item(
    item_name: Annotated[str, Field(description="准备寄运的物品名称")],
) -> dict:
    """寄件前预检物品风险，最终以承运商和目的国规则为准。"""
    text = item_name.lower()
    if any(word in text for word in ("炸药", "枪", "毒品", "放射性", "汽油", "烟花")):
        return {"decision": "prohibited", "reason": "属于常见明确禁寄高风险物品", "declaration_hint": "不得寄运，请勿虚假申报"}
    if any(word in text for word in ("电池", "液体", "粉末", "食品", "药品", "磁铁", "动植物")):
        return {"decision": "requires_review", "reason": "可能受承运商或目的国限制", "declaration_hint": "提供真实品名、数量、用途和包装信息，寄运前确认线路"}
    return {"decision": "可咨询寄运", "reason": "未命中常见禁限寄关键词", "declaration_hint": "仍需如实填写品名、数量和价值，并以承运商最终审核为准"}


registry.register(registry.spec_from_langchain_tool(query_shipment, source="builtin", inject_user_id=True))
registry.register(registry.spec_from_langchain_tool(assess_shipment_sla, source="builtin", inject_user_id=True))
registry.register(registry.spec_from_langchain_tool(estimate_shipping_fee, source="builtin"))
registry.register(registry.spec_from_langchain_tool(classify_logistics_exception, source="builtin"))
registry.register(registry.spec_from_langchain_tool(check_prohibited_item, source="builtin"))
