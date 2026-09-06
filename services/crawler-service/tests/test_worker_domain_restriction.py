from __future__ import annotations

import pytest
import pytest_asyncio
from ips_db import Base, Collection, CrawlJob, CrawlUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.worker import CrawlWorker


@pytest_asyncio.fixture
async def sessionmaker_(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def job_id(sessionmaker_):
    async with sessionmaker_() as session:
        collection = Collection(name="c", language="en")
        session.add(collection)
        await session.flush()
        job = CrawlJob(
            collection_id=collection.id,
            seed_urls=["https://example.com/"],
            max_documents=10,
            max_depth=2,
            allowed_domain="example.com",
        )
        session.add(job)
        await session.commit()
        return job.id


@pytest.mark.asyncio
async def test_enqueue_links_drops_other_domains_and_subdomains_when_restricted(sessionmaker_, job_id):
    worker = CrawlWorker(sessionmaker_, Settings())
    links = [
        "https://example.com/page-1",
        "https://en.example.com/page-2",
        "https://other.com/page-3",
    ]

    await worker._frontier.enqueue_links(job_id, discovered_from_id=1, depth=1, links=links, allowed_domain="example.com")

    async with sessionmaker_() as session:
        result = await session.execute(select(CrawlUrl.url).where(CrawlUrl.job_id == job_id))
        queued = {row[0] for row in result.all()}
    assert queued == {"https://example.com/page-1"}


@pytest.mark.asyncio
async def test_enqueue_links_keeps_all_domains_when_unrestricted(sessionmaker_, job_id):
    worker = CrawlWorker(sessionmaker_, Settings())
    links = ["https://example.com/page-1", "https://other.com/page-3"]

    await worker._frontier.enqueue_links(job_id, discovered_from_id=1, depth=1, links=links, allowed_domain=None)

    async with sessionmaker_() as session:
        result = await session.execute(select(CrawlUrl.url).where(CrawlUrl.job_id == job_id))
        queued = {row[0] for row in result.all()}
    assert queued == {"https://example.com/page-1", "https://other.com/page-3"}
