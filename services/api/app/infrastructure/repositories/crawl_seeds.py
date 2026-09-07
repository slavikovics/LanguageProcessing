from __future__ import annotations

from ips_db import CrawlSeed
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class CrawlSeedRepository:
    """CRUD for the persisted, per-collection crawl address list."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_collection(self, collection_id: int) -> list[CrawlSeed]:
        result = await self._session.execute(
            select(CrawlSeed).where(CrawlSeed.collection_id == collection_id).order_by(CrawlSeed.id)
        )
        return list(result.scalars().all())

    async def get(self, seed_id: int) -> CrawlSeed | None:
        return await self._session.get(CrawlSeed, seed_id)

    async def count_by_collection(self, collection_id: int) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(CrawlSeed).where(CrawlSeed.collection_id == collection_id)
        )
        return int(result.scalar_one())

    async def create(
        self,
        *,
        collection_id: int,
        url: str,
        max_documents: int,
        max_depth: int,
        same_domain_only: bool,
        language: str,
    ) -> CrawlSeed:
        seed = CrawlSeed(
            collection_id=collection_id,
            url=url,
            max_documents=max_documents,
            max_depth=max_depth,
            same_domain_only=same_domain_only,
            language=language,
        )
        self._session.add(seed)
        await self._session.flush()
        return seed

    async def update(
        self,
        seed: CrawlSeed,
        *,
        url: str,
        max_documents: int,
        max_depth: int,
        same_domain_only: bool,
        language: str,
    ) -> CrawlSeed:
        seed.url = url
        seed.max_documents = max_documents
        seed.max_depth = max_depth
        seed.same_domain_only = same_domain_only
        seed.language = language
        await self._session.flush()
        return seed

    async def delete(self, seed: CrawlSeed) -> None:
        await self._session.delete(seed)
