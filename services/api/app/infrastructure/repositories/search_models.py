from __future__ import annotations

from ips_db import SearchModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SearchModelRepository:
    """Reads the search_models registry seeded by migrations — adding a new
    model is a new seeded row, never a schema change."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(self, key: str) -> SearchModel | None:
        result = await self._session.execute(select(SearchModel).where(SearchModel.key == key))
        return result.scalars().first()

    async def list_active(self) -> list[SearchModel]:
        result = await self._session.execute(
            select(SearchModel).where(SearchModel.is_active.is_(True)).order_by(SearchModel.id)
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[SearchModel]:
        result = await self._session.execute(select(SearchModel).order_by(SearchModel.id))
        return list(result.scalars().all())
