from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.tools.builtin.logistics import estimate_shipping_fee

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


class ShippingFeeIn(BaseModel):
    origin: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=100)
    weight_kg: float = Field(gt=0, le=1000)
    transport_mode: str = Field(pattern="^(经济|标准|特快)$")


@router.post("/shipping-fee")
async def shipping_fee(body: ShippingFeeIn) -> dict:
    return await estimate_shipping_fee.ainvoke(body.model_dump())
