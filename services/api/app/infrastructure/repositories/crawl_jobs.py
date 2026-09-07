from __future__ import annotations

import datetime as dt

from ips_db import CrawlJob
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import CrawlJobStatus


class CrawlJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        collection_id: int,
        seed_urls: list[str],
        max_documents: int,
        max_depth: int,
        mode: str = "crawl",
        allowed_domain: str | None = None,
        language: str = "en",
    ) -> CrawlJob:
        job = CrawlJob(
            collection_id=collection_id,
            seed_urls=seed_urls,
            max_documents=max_documents,
            max_depth=max_depth,
            mode=mode,
            allowed_domain=allowed_domain,
            language=language,
            status=CrawlJobStatus.PENDING.value,
            urls_queued=len(seed_urls),
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: int) -> CrawlJob | None:
        return await self._session.get(CrawlJob, job_id)

    async def list(self, *, collection_id: int | None = None, limit: int = 50) -> list[CrawlJob]:
        query = select(CrawlJob).order_by(CrawlJob.id.desc()).limit(limit)
        if collection_id is not None:
            query = query.where(CrawlJob.collection_id == collection_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_pending(self) -> list[CrawlJob]:
        result = await self._session.execute(
            select(CrawlJob).where(CrawlJob.status == CrawlJobStatus.PENDING.value)
        )
        return list(result.scalars().all())

    async def mark_status(
        self,
        job_id: int,
        status: CrawlJobStatus,
        *,
        error_message: str | None = None,
    ) -> None:
        values: dict[str, object] = {"status": status.value}
        if status == CrawlJobStatus.RUNNING:
            values["started_at"] = dt.datetime.utcnow()
        if status.is_terminal:
            values["finished_at"] = dt.datetime.utcnow()
        if error_message is not None:
            values["error_message"] = error_message
        await self._session.execute(update(CrawlJob).where(CrawlJob.id == job_id).values(**values))
        await self._session.commit()
