
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from ips_db import CrawlJob, CrawlUrl
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True)
class CrawlUrlHandle:
    id: int
    url: str
    depth: int


class Frontier:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], links_per_page_cap: int) -> None:
        self._sessionmaker = sessionmaker
        self._links_per_page_cap = links_per_page_cap

    async def claim_next(self, job_id: int) -> CrawlUrlHandle | None:
        async with self._sessionmaker() as session:
            result = await session.execute(
                select(CrawlUrl)
                .where(
                    CrawlUrl.job_id == job_id,
                    CrawlUrl.status == "queued",
                )
                .order_by(CrawlUrl.depth, CrawlUrl.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            crawl_url = result.scalar_one_or_none()
            if crawl_url is None:
                return None
            crawl_url.status = "fetching"
            await session.execute(
                update(CrawlJob)
                .where(CrawlJob.id == job_id)
                .values(urls_queued=CrawlJob.urls_queued - 1)
            )
            await session.commit()
            return CrawlUrlHandle(id=crawl_url.id, url=crawl_url.url, depth=crawl_url.depth)

    async def enqueue_links(
        self,
        job_id: int,
        discovered_from_id: int,
        depth: int,
        links: list[str],
        *,
        allowed_domain: str | None = None,
    ) -> None:
        deduped = list(dict.fromkeys(links))
        if allowed_domain is not None:
            deduped = [url for url in deduped if urlsplit(url).netloc == allowed_domain]
        candidates = deduped[: self._links_per_page_cap]
        if not candidates:
            return
        async with self._sessionmaker() as session:
            existing = await session.execute(
                select(CrawlUrl.url).where(CrawlUrl.job_id == job_id, CrawlUrl.url.in_(candidates))
            )
            existing_urls = {row[0] for row in existing.all()}
            new_urls = [url for url in candidates if url not in existing_urls]
            if not new_urls:
                return
            session.add_all(
                CrawlUrl(
                    job_id=job_id,
                    url=url,
                    depth=depth,
                    status="queued",
                    discovered_from_id=discovered_from_id,
                )
                for url in new_urls
            )
            try:
                await session.execute(
                    update(CrawlJob)
                    .where(CrawlJob.id == job_id)
                    .values(urls_queued=CrawlJob.urls_queued + len(new_urls))
                )
                await session.commit()
            except IntegrityError:
                await session.rollback()
