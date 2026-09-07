"""BFS crawl worker: claims pending crawl_jobs one at a time, fetches pages
shallowest-first, and keeps crawl_jobs/crawl_urls updated so the api service
can report live progress by reading those same tables.

max_depth is a traversal preference, not a hard stop: a job keeps widening
past it rather than finishing short of max_documents (see Frontier.claim_next).
max_documents (or a genuinely exhausted, finite link graph) is what ends it.
"""

from __future__ import annotations

import asyncio
import datetime as dt

import httpx
from ips_db import CrawlJob
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.frontier import Frontier
from app.job_context import JobContext
from app.page_pipeline import PagePipeline
from app.robots import RobotsCache
from app.throttle import DomainThrottle

_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


class CrawlWorker:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], settings: Settings) -> None:
        self._sessionmaker = sessionmaker
        self._settings = settings
        self._throttle = DomainThrottle(settings.crawler_politeness_delay_seconds)
        self._frontier = Frontier(sessionmaker, settings.links_per_page_cap)
        self._pipeline = PagePipeline(sessionmaker, settings, self._frontier, self._throttle)

    async def run_forever(self) -> None:
        async with httpx.AsyncClient(
            headers={"User-Agent": self._settings.crawler_user_agent}
        ) as client:
            robots = RobotsCache(self._settings.crawler_user_agent, client)
            # Several crawl_jobs run concurrently instead of one at a time —
            # jobs on different domains don't wait on each other.
            running: dict[int, asyncio.Task[None]] = {}
            while True:
                running = {jid: task for jid, task in running.items() if not task.done()}
                slots = self._settings.max_concurrent_jobs - len(running)
                job_ids: list[int] = []
                if slots > 0:
                    try:
                        job_ids = await self._next_pending_job_ids(slots, exclude=set(running))
                    except Exception as exc:
                        # Transient DB hiccups shouldn't kill the whole worker process.
                        print(f"crawler-service: poll failed, will retry: {exc!r}", flush=True)
                for job_id in job_ids:
                    running[job_id] = asyncio.create_task(self._run_job(job_id, client, robots))
                await asyncio.sleep(self._settings.poll_interval_seconds if not running else 1.0)

    async def _next_pending_job_ids(self, limit: int, *, exclude: set[int]) -> list[int]:
        async with self._sessionmaker() as session:
            query = select(CrawlJob.id).where(CrawlJob.status == "pending")
            if exclude:
                query = query.where(CrawlJob.id.not_in(exclude))
            query = query.order_by(CrawlJob.id).limit(limit)
            result = await session.execute(query)
            return [row[0] for row in result.all()]

    async def _load_context(self, job_id: int) -> JobContext | None:
        async with self._sessionmaker() as session:
            result = await session.execute(
                select(
                    CrawlJob.id,
                    CrawlJob.collection_id,
                    CrawlJob.max_documents,
                    CrawlJob.max_depth,
                    CrawlJob.mode,
                    CrawlJob.allowed_domain,
                    CrawlJob.language,
                ).where(CrawlJob.id == job_id)
            )
            row = result.first()
            if row is None:
                return None
            return JobContext(
                id=row.id,
                collection_id=row.collection_id,
                language=row.language,
                max_documents=row.max_documents,
                max_depth=row.max_depth,
                mode=row.mode,
                allowed_domain=row.allowed_domain,
            )

    async def _current_progress(self, job_id: int) -> tuple[int, str]:
        async with self._sessionmaker() as session:
            result = await session.execute(
                select(CrawlJob.documents_fetched, CrawlJob.status).where(CrawlJob.id == job_id)
            )
            row = result.first()
            return (row.documents_fetched, row.status) if row else (0, "cancelled")

    async def _run_job(self, job_id: int, client: httpx.AsyncClient, robots: RobotsCache) -> None:
        await self._mark_job_status(job_id, "running", started=True)
        ctx = await self._load_context(job_id)
        if ctx is None:
            return
        try:
            await self._drain_frontier(ctx, client, robots)
            _, status = await self._current_progress(job_id)
            if status not in _TERMINAL_STATUSES:
                await self._mark_job_status(job_id, "completed")
        except Exception as exc:  # pragma: no cover - top-level safety net
            await self._mark_job_status(job_id, "failed", error=str(exc)[:1000])

    async def _drain_frontier(
        self, ctx: JobContext, client: httpx.AsyncClient, robots: RobotsCache
    ) -> None:
        """Runs several fetch lanes concurrently against one job's URL
        frontier, since a network-bound fetch used to fully block claiming
        and processing the next URL. Frontier.claim_next uses SELECT ... FOR
        UPDATE SKIP LOCKED, so lanes never double-claim.

        A lane finding the frontier empty can't just stop: a sibling lane may
        still be mid-fetch and about to enqueue more links, so "queue empty"
        alone doesn't mean "job done" — only "queue empty AND no lane in
        flight" does.

        `in_flight` also doubles as a budget reservation: a lane reserves a
        slot *before* claiming a URL, not after saving a document, so several
        lanes checking documents_fetched at once can't all see room for "one
        more" and collectively overshoot max_documents.
        """
        in_flight = 0
        lock = asyncio.Lock()

        async def lane() -> None:
            nonlocal in_flight
            while True:
                fetched, status = await self._current_progress(ctx.id)
                if status in _TERMINAL_STATUSES:
                    return
                async with lock:
                    if fetched + in_flight >= ctx.max_documents:
                        if in_flight == 0:
                            return
                        at_capacity = True
                    else:
                        in_flight += 1
                        at_capacity = False
                if at_capacity:
                    await asyncio.sleep(0.2)
                    continue
                handle = await self._frontier.claim_next(ctx.id)
                if handle is None:
                    async with lock:
                        in_flight -= 1
                        others_active = in_flight > 0
                    if not others_active:
                        return
                    await asyncio.sleep(0.2)
                    continue
                try:
                    await self._pipeline.process_url(ctx, handle, client, robots)
                finally:
                    async with lock:
                        in_flight -= 1

        concurrency = max(1, self._settings.max_concurrent_fetches_per_job)
        await asyncio.gather(*(lane() for _ in range(concurrency)))

    async def _mark_job_status(
        self, job_id: int, status: str, *, started: bool = False, error: str | None = None
    ) -> None:
        values: dict[str, object] = {"status": status}
        if started:
            values["started_at"] = dt.datetime.utcnow()
        if status in _TERMINAL_STATUSES:
            values["finished_at"] = dt.datetime.utcnow()
        if error is not None:
            values["error_message"] = error
        async with self._sessionmaker() as session:
            await session.execute(update(CrawlJob).where(CrawlJob.id == job_id).values(**values))
            await session.commit()
