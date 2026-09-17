import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


_connect_args = {"ssl": ssl._create_unverified_context()} if settings.database_ssl else {}
engine = create_async_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)
