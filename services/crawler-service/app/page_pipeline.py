
from __future__ import annotations

import datetime as dt

import httpx
from ips_db import Collection, CrawlJob, CrawlUrl, Document
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nlp_core.content_extraction import extract_main_content

from app.config import Settings
from app.fetcher import FetchError, extract_links, extract_title, fetch_html
from app.frontier import CrawlUrlHandle, Frontier
from app.job_context import JobContext
from app.robots import RobotsCache
from app.throttle import DomainThrottle


class PagePipeline:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        settings: Settings,
        frontier: Frontier,
        throttle: DomainThrottle,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._settings = settings
        self._frontier = frontier
        self._throttle = throttle

    async def process_url(
        self, ctx: JobContext, handle: CrawlUrlHandle, client: httpx.AsyncClient, robots: RobotsCache
    ) -> None:
        try:
            if not await robots.is_allowed(handle.url):
                await self._finish_url(handle.id, "blocked", error="disallowed by robots.txt")
                await self._bump_counters(ctx.id, urls_visited=1)
                return

            await self._throttle.wait(handle.url)
            html = await fetch_html(client, handle.url)
            text = extract_main_content(html)

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

    async def _touch_collection(self, session: AsyncSession, collection_id: int) -> None:
        collection = await session.get(Collection, collection_id)
        if collection is not None:
            collection.documents_changed_at = dt.datetime.utcnow()

    async def _save_document(self, ctx: JobContext, url: str, html: str, text: str) -> int | None:
        title = extract_title(html, fallback=url)
        async with self._sessionmaker() as session:
            if ctx.mode == "refresh":
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
