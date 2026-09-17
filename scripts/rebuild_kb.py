"""清理并重建当前场景知识库。"""
import asyncio

from sqlalchemy import text

from app.db.base import engine
from app.kb import milvus_client


async def main() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        await conn.execute(text("DELETE FROM knowledge_chunks"))
        await conn.execute(text("DELETE FROM qa_extraction_staging"))
        await conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    await engine.dispose()
    milvus_client.drop(milvus_client.get_client(), "knowledge")


if __name__ == "__main__":
    asyncio.run(main())
