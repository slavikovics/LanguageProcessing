from __future__ import annotations

from ips_db import CrawlJob, CrawlUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.crawl_jobs import build_crawl_job_config
from app.infrastructure.repositories import CrawlJobRepository, CrawlUrlRepository


class CrawlJobService:
    """Orchestrates the domain rules and the repositories inside one
    transaction — the only place that knows both exist."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = CrawlJobRepository(session)
        self._urls = CrawlUrlRepository(session)

    async def create_job(
        self,
        *,
        collection_id: int,
        seed_urls: list[str],
        max_documents: int,
        max_depth: int,
    ) -> CrawlJob:
        config = build_crawl_job_config(
            collection_id=collection_id,
            seed_urls=seed_urls,
            max_documents=max_documents,
            max_depth=max_depth,
        )
        job = await self._jobs.create(
            collection_id=config.collection_id,
            seed_urls=list(config.seed_urls),
            max_documents=config.max_documents,
            max_depth=config.max_depth,
        )
        await self._urls.bulk_enqueue(job.id, list(config.seed_urls), depth=0)
        await self._session.commit()
        return job

    async def list_jobs(self) -> list[CrawlJob]:
        return await self._jobs.list()

    async def get_progress(self, job_id: int) -> tuple[CrawlJob | None, list[CrawlUrl]]:
        job = await self._jobs.get(job_id)
        if job is None:
            return None, []
        recent_urls = await self._urls.list_by_job(job_id, limit=20)
        return job, recent_urls
