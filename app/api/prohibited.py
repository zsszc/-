from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.tools.builtin.logistics import check_prohibited_item

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


class ProhibitedItemIn(BaseModel):
    item_name: str = Field(min_length=1, max_length=200)


@router.post("/prohibited-item-check")
async def prohibited_item_check(body: ProhibitedItemIn) -> dict:
    return await check_prohibited_item.ainvoke(body.model_dump())
