from __future__ import annotations

import pytest
import pytest_asyncio
from ips_db import Base, Collection, CrawlJob, CrawlSeed, Document, IndexJob
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.collections import CollectionBusy, CollectionNotFound, CollectionService
from app.application.crawl_jobs import CrawlJobNotFound, CrawlJobService
from app.application.indexing import IndexingService, IndexJobNotFound
from app.domain.crawl_jobs import InvalidCrawlJobConfig
from app.domain.indexing import IndexingError


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    # SQLite ignores ON DELETE CASCADE unless foreign_keys is turned on per
    # connection — Postgres (production) enforces it unconditionally, so
    # this only matters for making the test's cascade assertions meaningful.
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):  # noqa: ARG001
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _make_collection(session_factory) -> int:
    async with session_factory() as session:
        collection = Collection(name="c", language="en")
        session.add(collection)
        await session.commit()
        return collection.id


@pytest.mark.asyncio
async def test_delete_collection_not_found(session_factory):
    async with session_factory() as session:
        with pytest.raises(CollectionNotFound):
            await CollectionService(session).delete(999)


@pytest.mark.asyncio
async def test_delete_collection_happy_path_cascades_documents(session_factory):
    collection_id = await _make_collection(session_factory)
    async with session_factory() as session:
        session.add(
            Document(
                collection_id=collection_id,
                title="d",
                url="https://example.com/a",
                clean_text="text",
                language="en",
                char_count=4,
            )
        )
        session.add(CrawlSeed(collection_id=collection_id, url="https://example.com/", max_documents=10, max_depth=1))
        await session.commit()

    async with session_factory() as session:
        await CollectionService(session).delete(collection_id)

    async with session_factory() as session:
        assert await session.get(Collection, collection_id) is None
        from sqlalchemy import func, select

        doc_count = await session.scalar(select(func.count()).select_from(Document))
        seed_count = await session.scalar(select(func.count()).select_from(CrawlSeed))
        assert doc_count == 0
        assert seed_count == 0


@pytest.mark.asyncio
async def test_delete_collection_blocked_while_indexing(session_factory):
    collection_id = await _make_collection(session_factory)
    async with session_factory() as session:
        session.add(IndexJob(collection_id=collection_id, status="running"))
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(CollectionBusy):
            await CollectionService(session).delete(collection_id)

    async with session_factory() as session:
        assert await session.get(Collection, collection_id) is not None


@pytest.mark.asyncio
async def test_delete_collection_allowed_after_indexing_completes(session_factory):
    collection_id = await _make_collection(session_factory)
    async with session_factory() as session:
        session.add(IndexJob(collection_id=collection_id, status="completed"))
        await session.commit()

    async with session_factory() as session:
        await CollectionService(session).delete(collection_id)

    async with session_factory() as session:
        assert await session.get(Collection, collection_id) is None


@pytest.mark.asyncio
async def test_recrawl_blocked_while_indexing(session_factory):
    collection_id = await _make_collection(session_factory)
    async with session_factory() as session:
        session.add(CrawlSeed(collection_id=collection_id, url="https://example.com/", max_documents=10, max_depth=1))
        session.add(IndexJob(collection_id=collection_id, status="pending"))
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(InvalidCrawlJobConfig, match="being indexed"):
            await CrawlJobService(session).run_collection_crawl(collection_id)


@pytest.mark.asyncio
async def test_refresh_blocked_while_indexing(session_factory):
    collection_id = await _make_collection(session_factory)
    async with session_factory() as session:
        session.add(
            Document(
                collection_id=collection_id,
                title="d",
                url="https://example.com/a",
                clean_text="text",
                language="en",
                char_count=4,
            )
        )
        session.add(IndexJob(collection_id=collection_id, status="running"))
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(InvalidCrawlJobConfig, match="being indexed"):
            await CrawlJobService(session).create_refresh_job(collection_id)


@pytest.mark.asyncio
async def test_recrawl_allowed_once_indexing_finished(session_factory):
    collection_id = await _make_collection(session_factory)
    async with session_factory() as session:
        session.add(CrawlSeed(collection_id=collection_id, url="https://example.com/", max_documents=10, max_depth=1))
        session.add(IndexJob(collection_id=collection_id, status="completed"))
        await session.commit()

    async with session_factory() as session:
        jobs = await CrawlJobService(session).run_collection_crawl(collection_id)
    assert len(jobs) == 1


@pytest.mark.asyncio
async def test_cancel_crawl_job_not_found(session_factory):
    async with session_factory() as session:
        with pytest.raises(CrawlJobNotFound):
            await CrawlJobService(session).cancel_job(999)


@pytest.mark.asyncio
async def test_cancel_crawl_job_already_terminal_is_rejected(session_factory):
    collection_id = await _make_collection(session_factory)
    async with session_factory() as session:
        job = CrawlJob(
            collection_id=collection_id, seed_urls=["https://example.com/"], max_documents=10, max_depth=1,
            status="completed",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    async with session_factory() as session:
        with pytest.raises(InvalidCrawlJobConfig, match="already completed"):
            await CrawlJobService(session).cancel_job(job_id)


@pytest.mark.asyncio
async def test_cancel_crawl_job_happy_path(session_factory):
    collection_id = await _make_collection(session_factory)
    async with session_factory() as session:
        job = CrawlJob(
            collection_id=collection_id, seed_urls=["https://example.com/"], max_documents=10, max_depth=1,
            status="running",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    async with session_factory() as session:
        cancelled = await CrawlJobService(session).cancel_job(job_id)
    assert cancelled.status == "cancelled"

    async with session_factory() as session:
        stored = await session.get(CrawlJob, job_id)
        assert stored.status == "cancelled"


@pytest.mark.asyncio
async def test_cancel_index_job_not_found(session_factory):
    async with session_factory() as session:
        with pytest.raises(IndexJobNotFound):
            await IndexingService(session).cancel_job(999)


@pytest.mark.asyncio
async def test_cancel_index_job_already_terminal_is_rejected(session_factory):
    collection_id = await _make_collection(session_factory)
    async with session_factory() as session:
        job = IndexJob(collection_id=collection_id, status="completed")
        session.add(job)
        await session.commit()
        job_id = job.id

    async with session_factory() as session:
        with pytest.raises(IndexingError, match="already completed"):
            await IndexingService(session).cancel_job(job_id)


@pytest.mark.asyncio
async def test_cancel_index_job_while_pending_prevents_it_from_ever_running(session_factory):
    """A job cancelled before the background task even started must stay
    cancelled — mark_running must not silently resurrect it back to
    "running" once the task does get around to it (see IndexJobRepository.
    mark_running's conditional UPDATE)."""
    collection_id = await _make_collection(session_factory)
    async with session_factory() as session:
        document = Document(
            collection_id=collection_id, title="d", url="https://example.com/a",
            clean_text="hello world", language="en", char_count=11,
        )
        session.add(document)
        job = IndexJob(collection_id=collection_id, status="pending")
        session.add(job)
        await session.commit()
        job_id = job.id

    async with session_factory() as session:
        await IndexingService(session).cancel_job(job_id)

    async with session_factory() as session:
        # The background task now gets around to running the (already
        # cancelled) job — it must notice immediately and do nothing.
        await IndexingService(session).run_job(job_id)

    async with session_factory() as session:
        stored = await session.get(IndexJob, job_id)
        assert stored.status == "cancelled"
        assert stored.documents_processed == 0
