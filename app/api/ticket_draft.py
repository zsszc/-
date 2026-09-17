from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.tools.builtin.logistics import classify_logistics_exception

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


class TicketDraftIn(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    tracking_no: str | None = Field(default=None, max_length=100)


@router.post("/ticket-draft")
async def ticket_draft(body: TicketDraftIn) -> dict:
    classified = await classify_logistics_exception.ainvoke({"description": body.description})
    tracking = f"（运单号：{body.tracking_no}）" if body.tracking_no else ""
    return {
        "ticket_type": "物流异常",
        "title": f"{classified['category']}{tracking}",
        "description": f"{body.description}{tracking}",
        "category": classified["category"],
        "severity": classified["severity"],
        "required_materials": classified["required_materials"],
        "requires_confirmation": True,
    }
