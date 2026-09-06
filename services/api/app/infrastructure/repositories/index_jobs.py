from __future__ import annotations

import datetime as dt

from ips_db import IndexJob
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import IndexJobStatus


class IndexJobRepository:
    """Tracks indexing progress the same way CrawlJobRepository tracks
    crawling — a DB row the frontend polls for a live progress bar."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, collection_id: int) -> IndexJob:
        job = IndexJob(collection_id=collection_id, status=IndexJobStatus.PENDING.value)
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: int) -> IndexJob | None:
        return await self._session.get(IndexJob, job_id)

    async def latest_for_collection(self, collection_id: int) -> IndexJob | None:
        result = await self._session.execute(
            select(IndexJob)
            .where(IndexJob.collection_id == collection_id)
            .order_by(IndexJob.id.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def mark_running(self, job_id: int, *, documents_total: int) -> bool:
        """Conditional UPDATE, not an ORM assignment: a job can be cancelled
        while still "pending", and an unconditional write would resurrect it
        into "running". Returns whether the transition happened."""
        result = await self._session.execute(
            update(IndexJob)
            .where(IndexJob.id == job_id, IndexJob.status == IndexJobStatus.PENDING.value)
            .values(
                status=IndexJobStatus.RUNNING.value,
                documents_total=documents_total,
                started_at=dt.datetime.utcnow(),
            )
        )
        await self._session.commit()
        return result.rowcount > 0

    async def update_progress(self, job_id: int, *, documents_processed: int) -> None:
        job = await self._session.get(IndexJob, job_id)
        if job is None:
            return
        job.documents_processed = documents_processed
        await self._session.commit()

    async def mark_completed(self, job_id: int, *, terms_indexed: int) -> None:
        job = await self._session.get(IndexJob, job_id)
        if job is None:
            return
        job.status = IndexJobStatus.COMPLETED.value
        job.terms_indexed = terms_indexed
        job.finished_at = dt.datetime.utcnow()
        await self._session.commit()

    async def mark_failed(self, job_id: int, *, error_message: str) -> None:
        job = await self._session.get(IndexJob, job_id)
        if job is None:
            return
        job.status = IndexJobStatus.FAILED.value
        job.error_message = error_message[:1000]
        job.finished_at = dt.datetime.utcnow()
        await self._session.commit()

    async def get_status(self, job_id: int) -> str | None:
        """Raw column read, bypassing the identity map: the running job's own
        long-lived session already has this row cached, so .get() would miss
        a concurrent cancel request's UPDATE."""
        result = await self._session.execute(select(IndexJob.status).where(IndexJob.id == job_id))
        row = result.first()
        return row[0] if row else None

    async def request_cancel(self, job_id: int) -> bool:
        """Marks a pending/running job cancelled; a no-op if it already
        finished on its own, so a race can't resurrect a finished job."""
        result = await self._session.execute(
            update(IndexJob)
            .where(IndexJob.id == job_id, IndexJob.status.in_(["pending", "running"]))
            .values(status=IndexJobStatus.CANCELLED.value, finished_at=dt.datetime.utcnow())
        )
        await self._session.commit()
        return result.rowcount > 0

    async def delete_all_by_collection(self, collection_id: int) -> None:
        await self._session.execute(delete(IndexJob).where(IndexJob.collection_id == collection_id))
