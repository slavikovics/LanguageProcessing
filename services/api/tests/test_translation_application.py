from __future__ import annotations

import pytest
import pytest_asyncio
from ips_db import Base, Collection, Document
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.translation import TranslationDictionaryService, TranslationService
from app.domain.translation import TranslationError
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories.translation import TranslationDictionaryRepository


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
        pass

    async def translate(self, text: str, dictionary: dict[str, str]) -> dict:
        return {
            "translated_text": f"[fr] {text}",
            "word_count": len(text.split()),
            "translated_word_count": 1,
            "words": [
                {"lemma": "cat", "pos": "NOUN", "surface": "cat", "frequency": 1, "translation": "chat"}
            ],
        }

    async def split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in text.split(".") if s.strip()]

    async def parse_sentence(self, text: str) -> list[dict]:
        return [
            {
                "position": 0,
                "text": text.split()[0] if text.split() else "",
                "lemma": "x",
                "pos": "NOUN",
                "dep": "ROOT",
                "head_position": None,
                "head_text": None,
                "morph": {},
                "is_punct": False,
            }
        ]


@pytest_asyncio.fixture
async def document_id(session_factory) -> int:
    async with session_factory() as session:
        collection = Collection(name="c", language="en")
        session.add(collection)
        await session.flush()
        document = Document(
            collection_id=collection.id, title="doc", clean_text="The cat sits.", language="en"
        )
        session.add(document)
        await session.commit()
        return document.id


@pytest.mark.asyncio
async def test_translate_from_document_persists_run_and_words(session_factory, document_id):
    async with session_factory() as session:
        service = TranslationService(session, nlp_client=_FakeNlpServiceClient())
        run = await service.translate(document_id=document_id, text=None)

        assert run.translated_text == "[fr] The cat sits."
        assert run.document_id == document_id
        assert run.source_lang == "en"
        assert run.target_lang == "fr"

        words = await service.get_run_words(run.id)
        assert len(words) == 1
        assert words[0].lemma == "cat"
        assert words[0].translation == "chat"


@pytest.mark.asyncio
async def test_translate_from_free_text_without_document(session_factory):
    async with session_factory() as session:
        service = TranslationService(session, nlp_client=_FakeNlpServiceClient())
        run = await service.translate(document_id=None, text="Hello world")
        assert run.document_id is None
        assert run.source_text == "Hello world"


@pytest.mark.asyncio
async def test_translate_requires_document_or_text(session_factory):
    async with session_factory() as session:
        service = TranslationService(session, nlp_client=_FakeNlpServiceClient())
        with pytest.raises(TranslationError):
            await service.translate(document_id=None, text=None)


@pytest.mark.asyncio
async def test_translate_unknown_document_raises(session_factory):
    async with session_factory() as session:
        service = TranslationService(session, nlp_client=_FakeNlpServiceClient())
        with pytest.raises(TranslationError):
            await service.translate(document_id=999, text=None)


@pytest.mark.asyncio
async def test_list_sentences_splits_run_source_text(session_factory, document_id):
    async with session_factory() as session:
        service = TranslationService(session, nlp_client=_FakeNlpServiceClient())
        run = await service.translate(document_id=document_id, text=None)
        sentences = await service.list_sentences(run.id)
        assert sentences == ["The cat sits"]


@pytest.mark.asyncio
async def test_parse_sentence_rejects_blank_text(session_factory):
    async with session_factory() as session:
        service = TranslationService(session, nlp_client=_FakeNlpServiceClient())
        with pytest.raises(TranslationError):
            await service.parse_sentence("   ")


@pytest.mark.asyncio
async def test_dictionary_as_lookup_builds_composite_keys(session_factory):
    async with session_factory() as session:
        repo = TranslationDictionaryRepository(session)
        await repo.create(
            source_lang="en", target_lang="fr", source_lemma="cat", pos="NOUN",
            target_text="chat", notes=None,
        )
        await repo.create(
            source_lang="en", target_lang="fr", source_lemma="fast", pos=None,
            target_text="rapide", notes=None,
        )
        await session.commit()

        lookup = await repo.as_lookup(source_lang="en", target_lang="fr")
        assert lookup["cat|NOUN"] == "chat"
        assert lookup["fast|*"] == "rapide"


@pytest.mark.asyncio
async def test_dictionary_service_rejects_duplicate_entry(session_factory):
    async with session_factory() as session:
        service = TranslationDictionaryService(session)
        await service.create(
            source_lang="en", target_lang="fr", source_lemma="cat", pos="NOUN",
            target_text="chat", notes=None,
        )
        with pytest.raises(TranslationError):
            await service.create(
                source_lang="en", target_lang="fr", source_lemma="cat", pos="NOUN",
                target_text="chat2", notes=None,
            )


@pytest.mark.asyncio
async def test_dictionary_service_update_and_delete(session_factory):
    async with session_factory() as session:
        service = TranslationDictionaryService(session)
        entry = await service.create(
            source_lang="en", target_lang="fr", source_lemma="cat", pos="NOUN",
            target_text="chat", notes=None,
        )
        updated = await service.update(entry.id, target_text="chatte")
        assert updated.target_text == "chatte"

        await service.delete(entry.id)
        with pytest.raises(TranslationError):
            await service.update(entry.id, target_text="x")
