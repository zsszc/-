"""ch09 飞轮入口3:用户反馈没解决。👎 落 low_confidence_questions(source=user_feedback),
快照尽力回捞(checkpointer 里最近一轮的 retrieved_snapshot,问题对得上才用);👍 只记日志。"""
import asyncio
import logging

from fastapi import APIRouter

from app.db import repository
from app.graph import runtime
from app.core.observability import score_session_feedback
from app.schemas.feedback import FeedbackRequest, FeedbackResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _same_question(a: str, b: str) -> bool:
    return "".join(a.split()) == "".join(b.split())


@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest) -> FeedbackResponse:
    # Langfuse 读写是同步 SDK，放线程池且安全降级，不卡 FastAPI 事件环。
    scored = await asyncio.to_thread(
        score_session_feedback, req.conversation_id, req.rating, req.question)
    if req.rating == "up":
        logger.info("feedback up conv=%s q=%r(只记日志,不落库)", req.conversation_id, req.question[:40])
        return FeedbackResponse(pooled=False, scored=scored)

    snapshot = None
    try:
        turn = await runtime.get_turn_snapshot(req.conversation_id)
        if turn["snapshot"] and _same_question(turn["question"], req.question):
            snapshot = turn["snapshot"]
    except Exception:
        logger.warning("feedback 快照回捞失败 conv=%s(照常落池)", req.conversation_id, exc_info=True)

    await repository.insert_low_confidence(
        req.conversation_id, req.question, "user_feedback", "用户反馈未解决",
        retrieved_chunks=snapshot,
    )
    logger.info("feedback down conv=%s 已落池 快照=%s", req.conversation_id,
                "有" if snapshot else "无")
    return FeedbackResponse(pooled=True, scored=scored)
