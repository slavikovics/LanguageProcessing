from collections.abc import AsyncIterator

from ips_db import Base
from ips_db.session import make_engine, make_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

settings = get_settings()

engine = make_engine(settings.database_url)
SessionLocal = make_sessionmaker(engine)

__all__ = ["Base", "engine", "SessionLocal", "get_db"]


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
