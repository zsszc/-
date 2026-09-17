from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.tools.builtin.logistics import classify_logistics_exception

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


class ExceptionClassifyIn(BaseModel):
    description: str = Field(min_length=1, max_length=2000, description="物流异常描述")


@router.post("/exception-classify")
async def exception_classify(body: ExceptionClassifyIn) -> dict:
    """把异常描述结构化，供前端和后续工单流程复用。"""
    return await classify_logistics_exception.ainvoke({"description": body.description})
