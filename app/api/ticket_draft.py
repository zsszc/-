from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.tools.builtin.logistics import classify_logistics_exception

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


class TicketDraftIn(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    tracking_no: str | None = Field(default=None, max_length=100)
    contact_name: str | None = Field(default=None, min_length=1, max_length=80)
    contact_phone: str | None = Field(default=None, pattern=r"^\+?[0-9 ()-]{7,20}$")
    evidence_items: list[str] = Field(default_factory=list, max_length=5)


@router.post("/ticket-draft")
async def ticket_draft(body: TicketDraftIn) -> dict:
    classified = await classify_logistics_exception.ainvoke({"description": body.description})
    tracking = f"（运单号：{body.tracking_no}）" if body.tracking_no else ""
    required_by_category = {
        "清关补料": ["tracking_no", "customs_notice"],
        "包裹破损或少件": ["tracking_no", "package_photos", "signing_record"],
        "疑似丢失": ["tracking_no", "shipping_proof", "value_proof"],
        "运输延误": ["tracking_no", "latest_tracking_screenshot"],
        "派送异常": ["tracking_no", "reachable_contact"],
    }
    required_fields = required_by_category.get(classified["category"], ["tracking_no", "description"])
    supplied = {"tracking_no": body.tracking_no, "contact_name": body.contact_name,
                "contact_phone": body.contact_phone, "description": body.description}
    supplied["evidence"] = body.evidence_items
    aliases = {"customs_notice": "海关通知或补料要求", "package_photos": "外包装和内件照片",
               "signing_record": "签收记录", "shipping_proof": "寄件凭证", "value_proof": "商品价值证明",
               "latest_tracking_screenshot": "最近轨迹截图", "reachable_contact": "可联系时间或备用联系方式"}
    missing_fields = [aliases.get(field, field) for field in required_fields
                      if not (supplied.get(field) or (field in {"customs_notice", "package_photos", "signing_record",
                                                               "shipping_proof", "value_proof", "latest_tracking_screenshot",
                                                               "reachable_contact"} and body.evidence_items))]
    return {
        "ticket_type": "物流异常",
        "title": f"{classified['category']}{tracking}",
        "description": f"{body.description}{tracking}",
        "category": classified["category"],
        "severity": classified["severity"],
        "required_materials": classified["required_materials"],
        "requires_confirmation": True,
        "field_validation": {"complete": not missing_fields, "required_fields": required_fields,
                              "missing_fields": missing_fields},
    }
