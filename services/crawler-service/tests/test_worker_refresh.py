from __future__ import annotations

import pytest
import pytest_asyncio
from ips_db import Base, Collection, Document
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.worker import CrawlWorker, JobContext


@pytest_asyncio.fixture
async def sessionmaker_(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_save_document_refresh_mode_updates_existing_row_in_place(sessionmaker_):
    async with sessionmaker_() as session:
        collection = Collection(name="c", language="en")
        session.add(collection)
        await session.flush()
        document = Document(
            collection_id=collection.id,
            title="Old title",
            url="https://example.com/a",
            clean_text="old text",
            language="en",
            char_count=8,
        )
        session.add(document)
        await session.commit()
        collection_id = collection.id
        document_id = document.id

    worker = CrawlWorker(sessionmaker_, Settings())
    ctx = JobContext(
        id=1, collection_id=collection_id, language="en", max_documents=10, max_depth=0, mode="refresh"
    )

    saved_id = await worker._save_document(
        ctx, "https://example.com/a", "<html><title>New title</title><body>x</body></html>", "new text"
    )
    assert saved_id == document_id

    async with sessionmaker_() as session:
        refreshed = await session.get(Document, document_id)
        assert refreshed.title == "New title"
        assert refreshed.clean_text == "new text"
        assert refreshed.char_count == len("new text")

        col = await session.get(Collection, collection_id)
        assert col.documents_changed_at is not None

    # Only one row for that URL — updated in place, not duplicated.
    async with sessionmaker_() as session:
        from sqlalchemy import func, select

        count = await session.scalar(
            select(func.count()).select_from(Document).where(Document.collection_id == collection_id)
        )
        assert count == 1


@pytest.mark.asyncio
async def test_save_document_crawl_mode_still_inserts_new_rows(sessionmaker_):
    async with sessionmaker_() as session:
        collection = Collection(name="c", language="en")
        session.add(collection)
        await session.commit()
        collection_id = collection.id

    worker = CrawlWorker(sessionmaker_, Settings())
    ctx = JobContext(
        id=1, collection_id=collection_id, language="en", max_documents=10, max_depth=0, mode="crawl"
    )

    saved_id = await worker._save_document(
        ctx, "https://example.com/new", "<html><title>Fresh</title><body>x</body></html>", "fresh text"
    )
    assert saved_id is not None

    async with sessionmaker_() as session:
        doc = await session.get(Document, saved_id)
        assert doc.url == "https://example.com/new"
        assert doc.clean_text == "fresh text"
