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
from dataclasses import dataclass

import httpx
from ips_db import Collection, CrawlJob, CrawlUrl, Document
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.content_extraction import extract_main_content
from app.fetcher import FetchError, extract_links, extract_title, fetch_html
from app.frontier import CrawlUrlHandle, Frontier
from app.robots import RobotsCache
from app.throttle import DomainThrottle

_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


@dataclass(frozen=True)
class JobContext:
    id: int
    collection_id: int
    language: str
    max_documents: int
    max_depth: int
    mode: str
    # Exact host (netloc) this job's discovered links must stay on — including
    # rejecting subdomains — or None when links may go anywhere.
    allowed_domain: str | None = None


class CrawlWorker:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], settings: Settings) -> None:
        self._sessionmaker = sessionmaker
        self._settings = settings
        self._throttle = DomainThrottle(settings.crawler_politeness_delay_seconds)
        self._frontier = Frontier(sessionmaker, settings.links_per_page_cap)

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

    # -- job lifecycle ----------------------------------------------------

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
                    Collection.language,
                )
                .join(Collection, Collection.id == CrawlJob.collection_id)
                .where(CrawlJob.id == job_id)
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
                    await self._process_url(ctx, handle, client, robots)
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

    async def _bump_counters(
        self,
        job_id: int,
        *,
        documents_fetched: int = 0,
        urls_visited: int = 0,
        urls_failed: int = 0,
    ) -> None:
        async with self._sessionmaker() as session:
            await session.execute(
                update(CrawlJob)
                .where(CrawlJob.id == job_id)
                .values(
                    documents_fetched=CrawlJob.documents_fetched + documents_fetched,
                    urls_visited=CrawlJob.urls_visited + urls_visited,
                    urls_failed=CrawlJob.urls_failed + urls_failed,
                )
            )
            await session.commit()

    # -- fetch + save one page ----------------------------------------------

    async def _touch_collection(self, session: AsyncSession, collection_id: int) -> None:
        """Marks the collection as changed now, so the UI can flag the index as stale."""
        collection = await session.get(Collection, collection_id)
        if collection is not None:
            collection.documents_changed_at = dt.datetime.utcnow()

    async def _save_document(self, ctx: JobContext, url: str, html: str, text: str) -> int | None:
        title = extract_title(html, fallback=url)
        async with self._sessionmaker() as session:
            if ctx.mode == "refresh":
                # Re-fetching a known URL updates the existing row instead of
                # inserting — a refresh brings documents up to date, not duplicates them.
                result = await session.execute(
                    select(Document).where(
                        Document.collection_id == ctx.collection_id, Document.url == url
                    )
                )
                existing = result.scalar_one_or_none()
                if existing is not None:
                    existing.title = title
                    existing.raw_html = html
                    existing.clean_text = text
                    existing.char_count = len(text)
                    existing.fetched_at = dt.datetime.utcnow()
                    await self._touch_collection(session, ctx.collection_id)
                    await session.commit()
                    return existing.id

            document = Document(
                collection_id=ctx.collection_id,
                title=title,
                url=url,
                raw_html=html,
                clean_text=text,
                language=ctx.language,
                char_count=len(text),
            )
            session.add(document)
            try:
                await self._touch_collection(session, ctx.collection_id)
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return None
            return document.id

    async def _process_url(
        self,
        ctx: JobContext,
        handle: CrawlUrlHandle,
        client: httpx.AsyncClient,
        robots: RobotsCache,
    ) -> None:
        try:
            if not await robots.is_allowed(handle.url):
                # "blocked", not "skipped": this page was never fetched, so it
                # was never actually a document candidate.
                await self._finish_url(handle.id, "blocked", error="disallowed by robots.txt")
                await self._bump_counters(ctx.id, urls_visited=1)
                return

            await self._throttle.wait(handle.url)
            html = await fetch_html(client, handle.url)
            text = extract_main_content(html)

            # The page fetched fine even when we don't keep it as a document
            # (too short, duplicate) — its links are still real discoveries,
            # so enqueue them before recording the skip.
            async def _enqueue_discovered_links() -> None:
                links = extract_links(html, handle.url)
                await self._frontier.enqueue_links(
                    ctx.id, handle.id, handle.depth + 1, links, allowed_domain=ctx.allowed_domain
                )

            if len(text) < self._settings.min_document_chars:
                await _enqueue_discovered_links()
                await self._finish_url(
                    handle.id, "skipped", error="document too short after cleanup"
                )
                await self._bump_counters(ctx.id, urls_visited=1)
                return

            document_id = await self._save_document(ctx, handle.url, html, text)
            if document_id is None:
                await _enqueue_discovered_links()
                await self._finish_url(handle.id, "skipped", error="duplicate document url")
                await self._bump_counters(ctx.id, urls_visited=1)
                return

            await self._finish_url(handle.id, "success", document_id=document_id)
            await self._bump_counters(ctx.id, urls_visited=1, documents_fetched=1)
            await _enqueue_discovered_links()

        except (FetchError, httpx.HTTPError) as exc:
            await self._finish_url(handle.id, "failed", error=str(exc)[:500])
            await self._bump_counters(ctx.id, urls_failed=1)

    async def _finish_url(
        self,
        crawl_url_id: int,
        status: str,
        *,
        document_id: int | None = None,
        error: str | None = None,
    ) -> None:
        async with self._sessionmaker() as session:
            await session.execute(
                update(CrawlUrl)
                .where(CrawlUrl.id == crawl_url_id)
                .values(
                    status=status,
                    document_id=document_id,
                    error=error,
                    fetched_at=dt.datetime.utcnow(),
                )
            )
            await session.commit()
