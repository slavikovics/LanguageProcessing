from __future__ import annotations

from urllib.parse import urlsplit

from ips_db import CrawlJob, CrawlUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.crawl_jobs import InvalidCrawlJobConfig, build_crawl_job_config, build_refresh_job_config
from app.domain.enums import CrawlJobStatus
from app.infrastructure.repositories.collections import CollectionRepository
from app.infrastructure.repositories.crawl_jobs import CrawlJobRepository
from app.infrastructure.repositories.crawl_seeds import CrawlSeedRepository
from app.infrastructure.repositories.crawl_urls import CrawlUrlRepository
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.index_jobs import IndexJobRepository


_ACTIVE_INDEX_STATUSES = {"pending", "running"}
_ACTIVE_CRAWL_STATUSES = {"pending", "running"}


class CrawlJobNotFound(Exception):
    pass


class CrawlJobService:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = CrawlJobRepository(session)
        self._urls = CrawlUrlRepository(session)
        self._documents = DocumentRepository(session)
        self._seeds = CrawlSeedRepository(session)
        self._index_jobs = IndexJobRepository(session)
        self._collections = CollectionRepository(session)

    async def _ensure_not_indexing(self, collection_id: int) -> None:
        latest = await self._index_jobs.latest_for_collection(collection_id)
        if latest is not None and latest.status in _ACTIVE_INDEX_STATUSES:
            raise InvalidCrawlJobConfig(
                "collection is being indexed; wait for indexing to finish before crawling or refreshing it"
            )

    async def create_job(
        self,
        *,
        collection_id: int,
        seed_urls: list[str],
        max_documents: int,
        max_depth: int,
    ) -> CrawlJob:
        await self._ensure_not_indexing(collection_id)
        config = build_crawl_job_config(
            collection_id=collection_id,
            seed_urls=seed_urls,
            max_documents=max_documents,
            max_depth=max_depth,
        )
        collection = await self._collections.get(collection_id)
        job = await self._jobs.create(
            collection_id=config.collection_id,
            seed_urls=list(config.seed_urls),
            max_documents=config.max_documents,
            max_depth=config.max_depth,
            language=collection.language if collection else "en",
        )
        await self._urls.bulk_enqueue(job.id, list(config.seed_urls), depth=0)
        await self._session.commit()
        return job

    async def create_refresh_job(self, collection_id: int) -> CrawlJob:
        await self._ensure_not_indexing(collection_id)
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
        await self._ensure_not_indexing(collection_id)
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
                language=seed.language,
            )
            await self._urls.bulk_enqueue(job.id, [seed.url], depth=0)
            jobs.append(job)

        await self._session.commit()
        return jobs

    async def cancel_job(self, job_id: int) -> CrawlJob:
        job = await self._jobs.get(job_id)
        if job is None:
            raise CrawlJobNotFound(f"crawl job {job_id} not found")
        if job.status not in _ACTIVE_CRAWL_STATUSES:
            raise InvalidCrawlJobConfig(f"crawl job {job_id} is already {job.status}")
        await self._jobs.mark_status(job_id, CrawlJobStatus.CANCELLED)
        job.status = CrawlJobStatus.CANCELLED.value
        return job

    async def list_jobs(self, *, collection_id: int | None = None) -> list[CrawlJob]:
        return await self._jobs.list(collection_id=collection_id)

    async def get_progress(self, job_id: int) -> tuple[CrawlJob | None, list[CrawlUrl]]:
        job = await self._jobs.get(job_id)
        if job is None:
            return None, []
        recent_urls = await self._urls.list_by_job(job_id, limit=20)
        return job, recent_urls
