from __future__ import annotations

import math

import pytest
import pytest_asyncio
from ips_db import Base, Collection, Document, DocumentSummary, Term
from ips_db.models.documents import DocumentTerm
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.summarization.document_summarizer import DocumentSummarizationService
from app.application.summarization.term_weights import compute_modified_term_weights
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.summarization_client import SummarizationServiceClient


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed_two_document_collection(session_factory) -> tuple[int, int]:
    async with session_factory() as session:
        collection = Collection(name="c", language="en")
        session.add(collection)
        await session.flush()

        doc_a = Document(
            collection_id=collection.id,
            title="A",
            clean_text="Lasers are devices. A red laser and a blue laser differ.",
            language="en",
        )
        doc_b = Document(
            collection_id=collection.id, title="B", clean_text="Dogs bark loudly.", language="en"
        )
        session.add_all([doc_a, doc_b])
        await session.flush()

        laser = Term(lemma="laser", language="en")
        device = Term(lemma="device", language="en")
        dog = Term(lemma="dog", language="en")
        session.add_all([laser, device, dog])
        await session.flush()

        session.add_all(
            [
                DocumentTerm(document_id=doc_a.id, term_id=laser.id, tf=3),
                DocumentTerm(document_id=doc_a.id, term_id=device.id, tf=1),
                DocumentTerm(document_id=doc_b.id, term_id=dog.id, tf=1),
            ]
        )
        await session.commit()
        return doc_a.id, doc_b.id


class _FakeSummarizationClient(SummarizationServiceClient):
    def __init__(self) -> None:
        pass

    async def _select(self, sentences: list[str], sentence_count: int) -> dict:
        selected = sentences[:sentence_count]
        return {
            "selected": [{"index": i, "text": s, "weight": 1.0} for i, s in enumerate(selected)],
            "total_sentences": len(sentences),
            "elapsed_ms": 1.0,
        }

    async def summarize_algorithmic(self, text, term_weights, sentence_count) -> dict:
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        return await self._select(sentences, sentence_count)

    async def summarize_textrank(self, text, sentence_count) -> dict:
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        return await self._select(sentences, sentence_count)

    async def summarize_embeddings(self, sentences, embeddings, sentence_count) -> dict:
        return await self._select(sentences, sentence_count)

    async def extract_keyword_hierarchy(self, text, term_weights, *, top_n=15, max_children=5):
        ranked = sorted(term_weights.items(), key=lambda pair: pair[1], reverse=True)[:top_n]
        return [{"term": term, "children": []} for term, _ in ranked]


class _FakeNlpClient(NlpServiceClient):
    def __init__(self) -> None:
        pass

    async def split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in text.split(".") if s.strip()]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    async def polish(self, text: str, *, language: str | None = None) -> dict:
        return {"polished_markdown": f"Polished: {text}", "model": "fake/test-model"}


async def test_compute_modified_term_weights_matches_formula(session_factory):
    doc_a_id, _doc_b_id = await _seed_two_document_collection(session_factory)
    async with session_factory() as session:
        collection_id = (await session.get(Document, doc_a_id)).collection_id
        weights = await compute_modified_term_weights(
            session, document_id=doc_a_id, collection_id=collection_id
        )
    assert set(weights) == {"laser", "device"}
    # tf_max = 3 (laser); df(laser) = 1, df(device) = 1; |DB| = 2 documents
    assert math.isclose(weights["laser"], 0.5 * (1 + 3 / 3) * math.log(2 / 1))
    assert math.isclose(weights["device"], 0.5 * (1 + 1 / 3) * math.log(2 / 1))


async def test_compute_modified_term_weights_empty_for_unindexed_document(session_factory):
    _doc_a_id, doc_b_id = await _seed_two_document_collection(session_factory)
    async with session_factory() as session:
        collection = await session.execute(select(Collection))
        collection_id = collection.scalars().first().id
        empty_doc = Document(collection_id=collection_id, title="empty", clean_text="", language="en")
        session.add(empty_doc)
        await session.commit()
        weights = await compute_modified_term_weights(
            session, document_id=empty_doc.id, collection_id=collection_id
        )
    assert weights == {}


async def test_summarize_document_runs_all_methods_and_persists_summaries(session_factory):
    doc_a_id, _doc_b_id = await _seed_two_document_collection(session_factory)
    async with session_factory() as session:
        service = DocumentSummarizationService(
            session,
            nlp_client=_FakeNlpClient(),
            summarization_client=_FakeSummarizationClient(),
        )
        keywords, outcomes = await service.summarize_document(
            doc_a_id, methods=["algorithmic", "textrank", "embeddings"], sentence_count=1
        )
        document = await session.get(Document, doc_a_id)

        assert keywords[0].term == "laser"
        assert {o.method for o in outcomes} == {"algorithmic", "textrank", "embeddings"}
        for outcome in outcomes:
            assert len(outcome.sentences) == 1
            assert outcome.total_sentences == 2
            assert outcome.compression_ratio == pytest.approx(
                len(outcome.summary_text) / len(document.clean_text)
            )

        stored = (
            (await session.execute(select(DocumentSummary).where(DocumentSummary.document_id == doc_a_id)))
            .scalars()
            .all()
        )
        assert len(stored) == 3
        assert all(row.run_id is None for row in stored)
        assert all(row.total_chars == len(document.clean_text) for row in stored)


async def test_polish_summary_persists_and_returns_polished_text(session_factory):
    doc_a_id, _doc_b_id = await _seed_two_document_collection(session_factory)
    async with session_factory() as session:
        service = DocumentSummarizationService(
            session,
            nlp_client=_FakeNlpClient(),
            summarization_client=_FakeSummarizationClient(),
        )
        _keywords, outcomes = await service.summarize_document(
            doc_a_id, methods=["algorithmic"], sentence_count=1
        )
        summaries = await service.list_summaries(doc_a_id)
        polished_markdown, model = await service.polish_summary(summaries[0].id)

        assert polished_markdown.startswith("Polished:")
        assert model == "fake/test-model"
