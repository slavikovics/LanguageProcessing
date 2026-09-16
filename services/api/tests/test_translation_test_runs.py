from __future__ import annotations

import pytest
import pytest_asyncio
from ips_db import Base, Collection, Document
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.translation import TranslationService, TranslationTestRunService
from app.domain.translation import TranslationError
from app.infrastructure.nlp_client import NlpServiceClient


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


class _FakeNlpServiceClient(NlpServiceClient):
    def __init__(self) -> None:
        self.calls = 0

    async def translate(self, text: str, dictionary: dict[str, str]) -> dict:
        self.calls += 1
        return {
            "translated_text": f"[fr] {text} extra",
            "word_count": len(text.split()),
            "translated_word_count": 1,
            "words": [],
        }


@pytest_asyncio.fixture
async def collection_id(session_factory) -> int:
    async with session_factory() as session:
        collection = Collection(name="c", language="en")
        session.add(collection)
        await session.flush()
        session.add_all(
            [
                Document(collection_id=collection.id, title="A", clean_text="The cat sits.", language="en"),
                Document(collection_id=collection.id, title="B", clean_text="Dogs bark loudly.", language="en"),
            ]
        )
        await session.commit()
        return collection.id


@pytest.mark.asyncio
async def test_start_run_rejects_empty_collection(session_factory):
    async with session_factory() as session:
        collection = Collection(name="empty", language="en")
        session.add(collection)
        await session.commit()
        service = TranslationTestRunService(session)
        with pytest.raises(TranslationError):
            await service.start_run(collection.id)


@pytest.mark.asyncio
async def test_run_job_translates_all_documents_and_tracks_progress(session_factory, collection_id):
    fake_nlp = _FakeNlpServiceClient()
    async with session_factory() as session:
        translator = TranslationService(session, nlp_client=fake_nlp)
        service = TranslationTestRunService(session, translation_service=translator)
        run = await service.start_run(collection_id)
        await service.run_job(run.id)

        finished = await service.get_run(run.id)
        assert finished.status == "completed"
        assert finished.documents_total == 2
        assert finished.documents_processed == 2
        assert fake_nlp.calls == 2

        results = await service.get_run_results(run.id)
        assert len(results) == 2
        assert all(r.test_run_id == run.id for r in results)
        assert all(r.translated_text_word_count == r.word_count + 2 for r in results)

        summary = await service.get_run_summary(run.id)
        assert summary.documents_translated == 2
        assert summary.mean_translated_word_count == 1.0


@pytest.mark.asyncio
async def test_start_run_only_selects_documents_matching_source_language(session_factory):
    fake_nlp = _FakeNlpServiceClient()
    async with session_factory() as session:
        collection = Collection(name="mixed", language="en")
        session.add(collection)
        await session.flush()
        session.add_all(
            [
                Document(collection_id=collection.id, title="A", clean_text="The cat sits.", language="en"),
                Document(collection_id=collection.id, title="B", clean_text="Dogs bark loudly.", language="en"),
                Document(collection_id=collection.id, title="C", clean_text="Le chat dort.", language="fr"),
            ]
        )
        await session.commit()

        translator = TranslationService(session, nlp_client=fake_nlp)
        service = TranslationTestRunService(session, translation_service=translator)
        run = await service.start_run(collection.id, source_lang="en", target_lang="fr")
        await service.run_job(run.id)

        finished = await service.get_run(run.id)
        assert finished.documents_total == 2
        assert finished.documents_processed == 2
        assert fake_nlp.calls == 2

        results = await service.get_run_results(run.id)
        translated_titles = {
            (await session.get(Document, r.document_id)).title for r in results
        }
        assert translated_titles == {"A", "B"}


@pytest.mark.asyncio
async def test_start_run_rejects_collection_without_matching_language(session_factory):
    async with session_factory() as session:
        collection = Collection(name="fr-only", language="fr")
        session.add(collection)
        await session.flush()
        session.add(Document(collection_id=collection.id, title="A", clean_text="Bonjour.", language="fr"))
        await session.commit()

        service = TranslationTestRunService(session)
        with pytest.raises(TranslationError):
            await service.start_run(collection.id, source_lang="en", target_lang="fr")


@pytest.mark.asyncio
async def test_cancel_run_marks_cancelled(session_factory, collection_id):
    async with session_factory() as session:
        service = TranslationTestRunService(session)
        run = await service.start_run(collection_id)
        cancelled = await service.cancel_run(run.id)
        assert cancelled.status == "cancelled"

        with pytest.raises(TranslationError):
            await service.cancel_run(run.id)
