from __future__ import annotations

from ips_db import CrawlSeed
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.crawl_seeds import MAX_SEEDS_PER_COLLECTION, build_crawl_seed_config
from app.domain.crawl_jobs import InvalidCrawlJobConfig
from app.infrastructure.repositories.crawl_seeds import CrawlSeedRepository

_DUPLICATE_URL_MESSAGE = "this address is already configured for the collection"


class CrawlSeedNotFound(Exception):
    pass


class CrawlSeedService:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._seeds = CrawlSeedRepository(session)

    async def list_seeds(self, collection_id: int) -> list[CrawlSeed]:
        return await self._seeds.list_by_collection(collection_id)

    async def create_seed(
        self,
        collection_id: int,
        *,
        url: str,
        max_documents: int,
        max_depth: int,
        same_domain_only: bool,
        language: str = "en",
    ) -> CrawlSeed:
        existing = await self._seeds.count_by_collection(collection_id)
        if existing >= MAX_SEEDS_PER_COLLECTION:
            raise InvalidCrawlJobConfig(f"at most {MAX_SEEDS_PER_COLLECTION} addresses are allowed")
        config = build_crawl_seed_config(
            url=url,
            max_documents=max_documents,
            max_depth=max_depth,
            same_domain_only=same_domain_only,
            language=language,
        )
        try:
            seed = await self._seeds.create(
                collection_id=collection_id,
                url=config.url,
                max_documents=config.max_documents,
                max_depth=config.max_depth,
                same_domain_only=config.same_domain_only,
                language=config.language,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise InvalidCrawlJobConfig(_DUPLICATE_URL_MESSAGE) from exc
        return seed

    async def update_seed(
        self,
        seed_id: int,
        *,
        url: str,
        max_documents: int,
        max_depth: int,
        same_domain_only: bool,
        language: str = "en",
    ) -> CrawlSeed:
        seed = await self._seeds.get(seed_id)
        if seed is None:
            raise CrawlSeedNotFound(f"crawl seed {seed_id} not found")
        config = build_crawl_seed_config(
            url=url,
            max_documents=max_documents,
            max_depth=max_depth,
            same_domain_only=same_domain_only,
            language=language,
        )
        try:
            updated = await self._seeds.update(
                seed,
                url=config.url,
                max_documents=config.max_documents,
                max_depth=config.max_depth,
                same_domain_only=config.same_domain_only,
                language=config.language,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise InvalidCrawlJobConfig(_DUPLICATE_URL_MESSAGE) from exc
        return updated

    async def delete_seed(self, seed_id: int) -> None:
        seed = await self._seeds.get(seed_id)
        if seed is None:
            raise CrawlSeedNotFound(f"crawl seed {seed_id} not found")
        await self._seeds.delete(seed)
        await self._session.commit()
