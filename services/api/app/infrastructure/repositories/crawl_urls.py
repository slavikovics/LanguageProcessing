from __future__ import annotations

from ips_db import CrawlUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import CrawlUrlStatus


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

    _DOCUMENT_CANDIDATE_STATUSES = (
        CrawlUrlStatus.SUCCESS.value,
        CrawlUrlStatus.FAILED.value,
        CrawlUrlStatus.SKIPPED.value,
    )

    async def list_by_job(self, job_id: int, *, limit: int = 50) -> list[CrawlUrl]:
        result = await self._session.execute(
            select(CrawlUrl)
            .where(
                CrawlUrl.job_id == job_id,
                CrawlUrl.status.in_(self._DOCUMENT_CANDIDATE_STATUSES),
            )
            .order_by(CrawlUrl.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
