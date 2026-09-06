"""BFS crawl worker: claims pending crawl_jobs one at a time, fetches pages
shallowest-first, and keeps crawl_jobs/crawl_urls updated so
app.interface.routers.crawl_jobs (in the api service) can report live
progress by reading those same tables — see docs/PROJECT_PLAN.md, 3.1.

max_depth is a traversal preference, not a hard stop: a job keeps widening
past it rather than finishing short of max_documents (see _claim_next_url).
max_documents (or a genuinely exhausted, finite link graph) is what ends it.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from ips_db import Collection, CrawlJob, CrawlUrl, Document
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.content_extraction import extract_main_content
from app.fetcher import FetchError, extract_links, extract_title, fetch_html
from app.robots import RobotsCache

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


@dataclass(frozen=True)
class CrawlUrlHandle:
    id: int
    url: str
    depth: int


class DomainThrottle:
    """Enforces a minimum delay between requests to the same domain — locked
    per domain so concurrent fetchers (see CrawlWorker's per-job fetch pool)
    queue up cleanly instead of racing the same last-fetch timestamp and
    both firing at once."""

    def __init__(self, delay_seconds: float) -> None:
        self._delay = delay_seconds
        self._last_fetch: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, domain: str) -> asyncio.Lock:
        lock = self._locks.get(domain)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[domain] = lock
        return lock

    async def wait(self, url: str) -> None:
        domain = urlsplit(url).netloc
        async with self._lock_for(domain):
            now = time.monotonic()
            last = self._last_fetch.get(domain)
            if last is not None:
                elapsed = now - last
                if elapsed < self._delay:
                    await asyncio.sleep(self._delay - elapsed)
            self._last_fetch[domain] = time.monotonic()


class CrawlWorker:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], settings: Settings) -> None:
        self._sessionmaker = sessionmaker
        self._settings = settings
        self._throttle = DomainThrottle(settings.crawler_politeness_delay_seconds)

    async def run_forever(self) -> None:
        async with httpx.AsyncClient(
            headers={"User-Agent": self._settings.crawler_user_agent}
        ) as client:
            robots = RobotsCache(self._settings.crawler_user_agent, client)
            # Several crawl_jobs run concurrently (e.g. run_collection_crawl's
            # one-job-per-seed, or independent collections) instead of one at
            # a time — jobs on different domains no longer have to wait for
            # each other just because the worker only ever looked at one job.
            running: dict[int, asyncio.Task[None]] = {}
            while True:
                running = {jid: task for jid, task in running.items() if not task.done()}
                slots = self._settings.max_concurrent_jobs - len(running)
                job_ids: list[int] = []
                if slots > 0:
                    try:
                        job_ids = await self._next_pending_job_ids(slots, exclude=set(running))
                    except Exception as exc:
                        # Transient DB hiccups (e.g. the schema not migrated
                        # yet on first boot) should not kill the whole worker
                        # process — just log and retry on the next tick.
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
        frontier — fetching a page (network-bound, and rate-limited per
        domain by DomainThrottle) used to fully block claiming and
        processing the next one, even when there was nothing domain-specific
        to wait for. _claim_next_url uses SELECT ... FOR UPDATE SKIP LOCKED,
        so lanes never double-claim a URL.

        A lane that finds the frontier empty can't just stop: a sibling lane
        may still be mid-fetch and about to enqueue more links, so "queue
        empty" alone doesn't mean "job done" — only "queue empty AND no lane
        is in flight" does.

        `in_flight` also doubles as a budget reservation: a lane reserves a
        slot (counts itself against max_documents) *before* claiming a URL,
        not after saving a document, so several lanes checking
        documents_fetched at once can't all see room for "one more" and
        collectively overshoot max_documents.
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
                handle = await self._claim_next_url(ctx.id)
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

    # -- URL frontier -------------------------------------------------------

    async def _claim_next_url(self, job_id: int) -> CrawlUrlHandle | None:
        """Claims the shallowest queued URL, with no depth ceiling: max_depth
        is a starting preference (BFS naturally exhausts shallower URLs
        first via order_by), not a hard stop — a job keeps widening past it
        rather than finishing short of max_documents just because the
        original depth budget ran out. The job still terminates: the link
        graph reachable from a job's seed is finite, and _enqueue_links
        dedupes so retracing it can't loop forever."""
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
            # urls_queued tracks the current backlog (not a lifetime total),
            # so the UI's "В очереди" reflects what's actually left to do —
            # it must shrink here to match _enqueue_links growing it.
            await session.execute(
                update(CrawlJob)
                .where(CrawlJob.id == job_id)
                .values(urls_queued=CrawlJob.urls_queued - 1)
            )
            await session.commit()
            return CrawlUrlHandle(id=crawl_url.id, url=crawl_url.url, depth=crawl_url.depth)

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

    async def _enqueue_links(
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
        candidates = deduped[: self._settings.links_per_page_cap]
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
            await session.execute(
                update(CrawlJob)
                .where(CrawlJob.id == job_id)
                .values(urls_queued=CrawlJob.urls_queued + len(new_urls))
            )
            try:
                await session.commit()
            except IntegrityError:
                # A sibling fetch lane (see _drain_frontier) discovered and
                # inserted the same link between our SELECT above and this
                # COMMIT — uq_crawl_url_job_url caught the race. It's queued
                # either way, so drop this batch instead of failing the job.
                await session.rollback()

    # -- fetch + save one page ----------------------------------------------

    async def _touch_collection(self, session: AsyncSession, collection_id: int) -> None:
        """Marks the collection as changed *now* so the UI can flag the
        index as stale — see Collection.documents_changed_at."""
        collection = await session.get(Collection, collection_id)
        if collection is not None:
            collection.documents_changed_at = dt.datetime.utcnow()

    async def _save_document(self, ctx: JobContext, url: str, html: str, text: str) -> int | None:
        title = extract_title(html, fallback=url)
        async with self._sessionmaker() as session:
            if ctx.mode == "refresh":
                # Re-fetching a known URL: update the existing row in place
                # instead of inserting — a "refresh" is meant to bring
                # already-crawled documents up to date, not duplicate them.
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
                # "blocked", not "skipped" — this page was never fetched, so
                # unlike the skips below it was never actually a document
                # candidate; the api service's progress view relies on that
                # distinction to only list genuine candidates.
                await self._finish_url(handle.id, "blocked", error="disallowed by robots.txt")
                await self._bump_counters(ctx.id, urls_visited=1)
                return

            await self._throttle.wait(handle.url)
            html = await fetch_html(client, handle.url)
            text = extract_main_content(html)

            # The page fetched fine even when we end up not keeping it as a
            # document (too short, duplicate) — its links are still real
            # discoveries, so enqueue them before recording the skip. Losing
            # that page must not also lose everything it linked to.
            #
            # max_depth is not enforced here: it's a starting preference the
            # frontier follows (see _claim_next_url's shallowest-first
            # order), not a hard ceiling — a job keeps widening past it
            # rather than finishing short of max_documents. A run that hits
            # only skips/duplicates within its "intended" depth would
            # otherwise stall at, say, 16/30 with an empty queue even though
            # the site has plenty more pages to try.
            async def _enqueue_discovered_links() -> None:
                links = extract_links(html, handle.url)
                await self._enqueue_links(
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
