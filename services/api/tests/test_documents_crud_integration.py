from __future__ import annotations

import pytest
import pytest_asyncio
from ips_db import Base, Collection
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.documents import DocumentService
from app.domain.documents import DocumentError


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def collection_id(session_factory):
    async with session_factory() as session:
        collection = Collection(name="manual", language="en")
        session.add(collection)
        await session.commit()
        return collection.id


@pytest.mark.asyncio
async def test_create_update_delete_document(session_factory, collection_id):
    async with session_factory() as session:
        created = await DocumentService(session).create_document(
            collection_id, title="Cats", url="https://example.com/cats", clean_text="Cats are animals."
        )
    assert created.char_count == len("Cats are animals.")

    async with session_factory() as session:
        updated = await DocumentService(session).update_document(
            created.id, title="Cats!", url="https://example.com/cats", clean_text="Cats are great animals."
        )
    assert updated.title == "Cats!"
    assert updated.char_count == len("Cats are great animals.")

    async with session_factory() as session:
        await DocumentService(session).delete_document(created.id)

    async with session_factory() as session:
        from app.infrastructure.repositories.documents import DocumentRepository

        assert await DocumentRepository(session).get(created.id) is None


@pytest.mark.asyncio
async def test_create_document_rejects_duplicate_url_in_collection(session_factory, collection_id):
    async with session_factory() as session:
        await DocumentService(session).create_document(
            collection_id, title="Cats", url="https://example.com/cats", clean_text="Cats are animals."
        )

    async with session_factory() as session:
        with pytest.raises(DocumentError):
            await DocumentService(session).create_document(
                collection_id, title="Cats again", url="https://example.com/cats", clean_text="More cats."
            )


@pytest.mark.asyncio
async def test_create_document_rejects_unknown_collection(session_factory):
    async with session_factory() as session:
        with pytest.raises(DocumentError):
            await DocumentService(session).create_document(
                999, title="Cats", url="https://example.com/cats", clean_text="Cats are animals."
            )


@pytest.mark.asyncio
async def test_update_document_rejects_unknown_id(session_factory):
    async with session_factory() as session:
        with pytest.raises(DocumentError):
            await DocumentService(session).update_document(
                999, title="Cats", url="https://example.com/cats", clean_text="Cats are animals."
            )


@pytest.mark.asyncio
async def test_delete_document_rejects_unknown_id(session_factory):
    async with session_factory() as session:
        with pytest.raises(DocumentError):
            await DocumentService(session).delete_document(999)


@pytest.mark.asyncio
async def test_create_document_without_url_is_allowed(session_factory, collection_id):
    async with session_factory() as session:
        created = await DocumentService(session).create_document(
            collection_id, title="Note", url=None, clean_text="A manually authored note."
        )
    assert created.url is None

    async with session_factory() as session:
        second = await DocumentService(session).create_document(
            collection_id, title="Another note", url="", clean_text="Another manually authored note."
        )
    assert second.url is None


@pytest.mark.asyncio
async def test_document_mutations_touch_collection_documents_changed_at(session_factory, collection_id):
    from app.infrastructure.repositories.collections import CollectionRepository

    async with session_factory() as session:
        collection = await CollectionRepository(session).get(collection_id)
        assert collection.documents_changed_at is None

    async with session_factory() as session:
        created = await DocumentService(session).create_document(
            collection_id, title="Cats", url="https://example.com/cats", clean_text="Cats are animals."
        )

    async with session_factory() as session:
        collection = await CollectionRepository(session).get(collection_id)
        assert collection.documents_changed_at is not None
        after_create = collection.documents_changed_at

    async with session_factory() as session:
        await DocumentService(session).delete_document(created.id)

    async with session_factory() as session:
        collection = await CollectionRepository(session).get(collection_id)
        assert collection.documents_changed_at >= after_create
