from __future__ import annotations

import pytest
import pytest_asyncio
from ips_db import Base, Collection, CrawlJob, CrawlUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.job_context import JobContext
from app.worker import CrawlWorker


@pytest_asyncio.fixture
async def sessionmaker_(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


class _AllowAllRobots:
    async def is_allowed(self, url: str) -> bool:
        return True


@pytest.mark.asyncio
async def test_drain_frontier_runs_lanes_concurrently_without_overshooting_budget(
    sessionmaker_, monkeypatch
):
    """Several fetch lanes race to claim URLs and each independently sees
    "room for one more" against a stale documents_fetched count — the
    in_flight reservation in _drain_frontier must stop that from adding up
    to more than max_documents saved documents."""
    async with sessionmaker_() as session:
        collection = Collection(name="c", language="en")
        session.add(collection)
        await session.flush()
        collection_id = collection.id
        job = CrawlJob(
            collection_id=collection_id,
            seed_urls=["https://example.com/0"],
            max_documents=3,
            max_depth=1,
        )
        session.add(job)
        await session.flush()
        job_id = job.id
        session.add_all(
            CrawlUrl(job_id=job_id, url=f"https://example.com/{i}", depth=0, status="queued")
            for i in range(10)
        )
        await session.commit()

    settings = Settings(max_concurrent_fetches_per_job=4, crawler_politeness_delay_seconds=0.0)
    worker = CrawlWorker(sessionmaker_, settings)

    async def fake_fetch_html(client, url):
        return "<html><title>t</title><body>irrelevant, extract_main_content is mocked</body></html>"

    monkeypatch.setattr("app.page_pipeline.fetch_html", fake_fetch_html)
    monkeypatch.setattr("app.page_pipeline.extract_main_content", lambda html: "a" * 300)
    monkeypatch.setattr("app.page_pipeline.extract_links", lambda html, base_url: [])

    ctx = JobContext(
        id=job_id, collection_id=collection_id, language="en", max_documents=3, max_depth=1, mode="crawl"
    )
    await worker._drain_frontier(ctx, client=None, robots=_AllowAllRobots())

    async with sessionmaker_() as session:
        refreshed = await session.get(CrawlJob, job_id)
        assert refreshed.documents_fetched == 3

        remaining_queued = await session.execute(
            select(CrawlUrl).where(CrawlUrl.job_id == job_id, CrawlUrl.status == "queued")
        )
        # The frontier had 10 URLs but the budget was 3 — draining must stop
        # once the budget is met, leaving the rest untouched.
        assert len(remaining_queued.scalars().all()) > 0
