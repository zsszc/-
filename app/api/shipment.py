from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.tools.builtin.logistics import query_shipment

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


class ShipmentQueryIn(BaseModel):
    tracking_no: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=200)


@router.post("/shipment-query")
async def shipment_query(body: ShipmentQueryIn) -> dict:
    result = await query_shipment.ainvoke(body.model_dump())
    if result.get("code") == "shipment_not_owned":
        raise HTTPException(status_code=404, detail="没有找到您的这票运单")
    return result
