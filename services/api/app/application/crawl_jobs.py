from __future__ import annotations

from urllib.parse import urlsplit

from ips_db import CrawlJob, CrawlUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.crawl_jobs import InvalidCrawlJobConfig, build_crawl_job_config, build_refresh_job_config
from app.infrastructure.repositories import (
    CollectionRepository,
    CrawlJobRepository,
    CrawlSeedRepository,
    CrawlUrlRepository,
    DocumentRepository,
    IndexJobRepository,
)


class CrawlJobService:
    """Orchestrates the domain rules and the repositories inside one
    transaction — the only place that knows both exist."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = CrawlJobRepository(session)
        self._urls = CrawlUrlRepository(session)
        self._documents = DocumentRepository(session)
        self._seeds = CrawlSeedRepository(session)
        self._index_jobs = IndexJobRepository(session)
        self._collections = CollectionRepository(session)

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

    async def create_refresh_job(self, collection_id: int) -> CrawlJob:
        """Re-fetches every document in the collection that has a URL,
        updating each row in place — see docs on build_refresh_job_config
        and CrawlWorker's 'refresh' mode."""
        urls = await self._documents.list_urls_by_collection(collection_id)
        if not urls:
            raise InvalidCrawlJobConfig("collection has no documents with a URL to refresh")
        config = build_refresh_job_config(collection_id=collection_id, urls=urls)
        job = await self._jobs.create(
            collection_id=config.collection_id,
            seed_urls=list(config.seed_urls),
            max_documents=config.max_documents,
            max_depth=config.max_depth,
            mode="refresh",
        )
        await self._urls.bulk_enqueue(job.id, list(config.seed_urls), depth=0)
        await self._session.commit()
        return job

    async def run_collection_crawl(self, collection_id: int) -> list[CrawlJob]:
        """Starts a fresh crawl of every configured CrawlSeed. Each seed
        keeps its own max_documents/max_depth/same_domain_only, so it
        becomes its own CrawlJob rather than sharing one job-wide budget —
        the worker already processes crawl_jobs one at a time, so seeds
        effectively crawl in order.

        A recrawl replaces the collection outright: existing documents (and,
        via DB cascade, their index rows and any qrels/results pointing at
        them) and the index-job history are deleted first, so the result
        only ever reflects the current seed list, never a mix of old and
        new crawls.
        """
        seeds = await self._seeds.list_by_collection(collection_id)
        if not seeds:
            raise InvalidCrawlJobConfig("collection has no configured crawl addresses")

        await self._documents.delete_all_by_collection(collection_id)
        await self._index_jobs.delete_all_by_collection(collection_id)
        await self._collections.touch_documents_changed(collection_id)

        jobs: list[CrawlJob] = []
        for seed in seeds:
            allowed_domain = urlsplit(seed.url).netloc if seed.same_domain_only else None
            job = await self._jobs.create(
                collection_id=collection_id,
                seed_urls=[seed.url],
                max_documents=seed.max_documents,
                max_depth=seed.max_depth,
                allowed_domain=allowed_domain,
            )
            await self._urls.bulk_enqueue(job.id, [seed.url], depth=0)
            jobs.append(job)

        await self._session.commit()
        return jobs

    async def list_jobs(self) -> list[CrawlJob]:
        return await self._jobs.list()

    async def get_progress(self, job_id: int) -> tuple[CrawlJob | None, list[CrawlUrl]]:
        job = await self._jobs.get(job_id)
        if job is None:
            return None, []
        recent_urls = await self._urls.list_by_job(job_id, limit=20)
        return job, recent_urls
