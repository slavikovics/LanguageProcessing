from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ips_db import Collection, CrawlJob, CrawlUrl, Document

from app.domain.enums import CrawlJobStatus, CrawlUrlStatus


class CollectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str, language: str) -> Collection:
        collection = Collection(name=name, language=language)
        self._session.add(collection)
        await self._session.flush()
        return collection

    async def get(self, collection_id: int) -> Collection | None:
        return await self._session.get(Collection, collection_id)

    async def list(self) -> list[Collection]:
        result = await self._session.execute(select(Collection).order_by(Collection.id))
        return list(result.scalars().all())


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_collection(self, collection_id: int, *, limit: int = 50, offset: int = 0) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.collection_id == collection_id)
            .order_by(Document.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get(self, document_id: int) -> Document | None:
        return await self._session.get(Document, document_id)

    async def count_by_collection(self, collection_id: int) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Document).where(Document.collection_id == collection_id)
        )
        return int(result.scalar_one())


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
    ) -> CrawlJob:
        job = CrawlJob(
            collection_id=collection_id,
            seed_urls=seed_urls,
            max_documents=max_documents,
            max_depth=max_depth,
            status=CrawlJobStatus.PENDING.value,
            urls_queued=len(seed_urls),
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: int) -> CrawlJob | None:
        return await self._session.get(CrawlJob, job_id)

    async def list(self, *, limit: int = 50) -> list[CrawlJob]:
        result = await self._session.execute(
            select(CrawlJob).order_by(CrawlJob.id.desc()).limit(limit)
        )
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


class CrawlUrlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_enqueue(
        self, job_id: int, urls: list[str], *, depth: int, discovered_from_id: int | None = None
    ) -> list[CrawlUrl]:
        entries = [
            CrawlUrl(
                job_id=job_id,
                url=url,
                depth=depth,
                status=CrawlUrlStatus.QUEUED.value,
                discovered_from_id=discovered_from_id,
            )
            for url in urls
        ]
        self._session.add_all(entries)
        await self._session.flush()
        return entries

    async def list_by_job(self, job_id: int, *, limit: int = 50) -> list[CrawlUrl]:
        result = await self._session.execute(
            select(CrawlUrl)
            .where(CrawlUrl.job_id == job_id)
            .order_by(CrawlUrl.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
