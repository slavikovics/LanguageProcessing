
from __future__ import annotations

import re

import pytest
import pytest_asyncio
from ips_db import Base, Collection, Document, SearchModel
from nlp_core import metrics, weighting
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.indexing import IndexingService
from app.application.metrics import MetricsService
from app.application.search import SearchService
from app.infrastructure.nlp_client import NlpServiceClient

_WORD_RE = re.compile(r"[a-z]+")
_STOPWORDS = {"are", "to", "the", "and"}
_IRREGULAR = {"cats": "cat", "dogs": "dog", "animals": "animal", "galaxies": "galaxy"}


def _fake_lemmatize(text: str) -> list[str]:
    words = _WORD_RE.findall(text.lower())
    return [_IRREGULAR.get(w, w) for w in words if w not in _STOPWORDS]


class _InProcessNlpClient(NlpServiceClient):

    def __init__(self) -> None:
        pass

    async def lemmatize(self, text: str) -> list[str]:
        return _fake_lemmatize(text)

    async def lemmatize_batch(self, texts: list[str]) -> list[list[str]]:
        return [_fake_lemmatize(t) for t in texts]

    async def index(self, document_term_lists: list[list[str]]) -> dict:
        total = len(document_term_lists)
        df = weighting.document_frequencies(document_term_lists)
        idf = weighting.inverse_document_frequency(df, total)
        term_frequencies = [weighting.term_frequencies(terms) for terms in document_term_lists]
        vectors = [weighting.normalized_tfidf_vector(tf, idf) for tf in term_frequencies]
        return {"idf": idf, "term_frequencies": term_frequencies, "vectors": vectors}

    async def idf_from_frequency(self, document_frequency, total_documents) -> dict:
        return weighting.inverse_document_frequency(document_frequency, total_documents)

    async def document_vector(self, term_frequencies, idf) -> dict:
        return weighting.normalized_tfidf_vector(term_frequencies, idf)

    async def evaluate_metrics(self, ranked_ids, relevant_ids) -> dict:
        relevant = set(relevant_ids)
        n = len(ranked_ids)
        precision_at_5 = metrics.precision_at_k(ranked_ids, relevant, 5)
        precision_at_10 = metrics.precision_at_k(ranked_ids, relevant, 10)
        recall_at_5 = metrics.recall_at_k(ranked_ids, relevant, 5)
        recall_at_10 = metrics.recall_at_k(ranked_ids, relevant, 10)
        return {
            "retrieved_count": n,
            "relevant_count": len(relevant),
            "precision_at_5": precision_at_5,
            "precision_at_10": precision_at_10,
            "recall_at_5": recall_at_5,
            "recall_at_10": recall_at_10,
            "f1_at_5": metrics.f1_score(precision_at_5, recall_at_5),
            "f1_at_10": metrics.f1_score(precision_at_10, recall_at_10),
            "average_precision": metrics.average_precision(ranked_ids, relevant),
            "r_precision": metrics.r_precision(ranked_ids, relevant),
            "curve": metrics.interpolated_precision_recall(ranked_ids, relevant),
        }

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            bucket = [0.0] * 8
            for word in _fake_lemmatize(text):
                bucket[hash(word) % 8] += 1.0
            norm = sum(v * v for v in bucket) ** 0.5
            vectors.append([v / norm for v in bucket] if norm else bucket)
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]


DOCS = [
    ("Cats", "https://example.com/cats", "Cats are small domestic animals. Cats like to sleep."),
    ("Dogs", "https://example.com/dogs", "Dogs are loyal domestic animals. Dogs like to run."),
    ("Astronomy", "https://example.com/space", "Stars and galaxies fill the universe."),
]


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
    async with factory() as session:
        session.add_all(
            [
                SearchModel(key="tfidf", label="TF-IDF", kind="tfidf", dimension=None, is_active=True),
                SearchModel(
                    key="gte-multilingual-base",
                    label="GTE Multilingual Base",
                    kind="dense_embedding",
                    dimension=768,
                    is_active=True,
                ),
            ]
        )
        await session.commit()
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def collection_with_documents(session_factory):
    async with session_factory() as session:
        collection = Collection(name="pets", language="en")
        session.add(collection)
        await session.flush()
        for title, url, text in DOCS:
            session.add(
                Document(
                    collection_id=collection.id,
                    title=title,
                    url=url,
                    clean_text=text,
                    language="en",
                    char_count=len(text),
                )
            )
        await session.commit()
        return collection.id


@pytest.mark.asyncio
async def test_full_pipeline_index_search_judge_metrics(session_factory, collection_with_documents):
    collection_id = collection_with_documents
    nlp = _InProcessNlpClient()

    async with session_factory() as session:
        summary = await IndexingService(session, nlp).reindex_collection_now(collection_id)
    assert summary.documents_indexed == 6
    assert summary.terms_indexed > 0

    async with session_factory() as session:
        response = await SearchService(session, nlp).search(
            collection_id=collection_id, text="cats domestic animals", top_k=10
        )
    assert response.hits, "expected at least one ranked document"
    assert response.hits[0].title == "Cats"
    assert "cat" in response.hits[0].matched_terms
    assert all(hit.title != "Astronomy" for hit in response.hits)

    cats_doc_id = response.hits[0].document_id
    dogs_hit = next((h for h in response.hits if h.title == "Dogs"), None)

    async with session_factory() as session:
        from app.infrastructure.repositories.judgments import RelevanceJudgmentRepository

        judgments = RelevanceJudgmentRepository(session)
        await judgments.set_judgment(
            query_id=response.query_id, document_id=cats_doc_id, is_relevant=True
        )
        if dogs_hit is not None:
            await judgments.set_judgment(
                query_id=response.query_id, document_id=dogs_hit.document_id, is_relevant=False
            )
        await session.commit()

    async with session_factory() as session:
        query_metrics = await MetricsService(session, nlp).evaluate_run(response.search_run_id)
    assert query_metrics.relevant_count == 1
    assert query_metrics.average_precision > 0
    assert len(query_metrics.curve) == 11

    async with session_factory() as session:
        collection_summary = await MetricsService(session, nlp).collection_summary(collection_id)
    assert len(collection_summary.queries) == 1
    assert collection_summary.map == pytest.approx(query_metrics.average_precision)
    assert len(collection_summary.curve) == 11
    assert collection_summary.model == "tfidf"


@pytest.mark.asyncio
async def test_metrics_are_scoped_per_model(session_factory, collection_with_documents):
    collection_id = collection_with_documents
    nlp = _InProcessNlpClient()

    async with session_factory() as session:
        await IndexingService(session, nlp).reindex_collection_now(collection_id)

    async with session_factory() as session:
        tfidf_response = await SearchService(session, nlp).search(
            collection_id=collection_id, text="cats domestic animals", top_k=10, model="tfidf"
        )
    cats_doc_id = tfidf_response.hits[0].document_id

    async with session_factory() as session:
        from app.infrastructure.repositories.judgments import RelevanceJudgmentRepository
        from app.infrastructure.repositories.queries import QueryRepository
        from app.infrastructure.repositories.search_models import SearchModelRepository

        embedding_model = await SearchModelRepository(session).get_by_key("gte-multilingual-base")
        queries = QueryRepository(session)
        query_row = await queries.get_or_create_query(collection_id=collection_id, text=tfidf_response.query_text)
        assert query_row.id == tfidf_response.query_id
        embedding_run = await queries.create_search_run(query_id=query_row.id, model_id=embedding_model.id)
        await queries.bulk_insert_results(embedding_run.id, [(cats_doc_id, 1, 0.9)])

        await RelevanceJudgmentRepository(session).set_judgment(
            query_id=tfidf_response.query_id, document_id=cats_doc_id, is_relevant=True
        )
        await session.commit()
        embedding_run_id = embedding_run.id

    async with session_factory() as session:
        tfidf_summary = await MetricsService(session, nlp).collection_summary(collection_id, model="tfidf")
    async with session_factory() as session:
        embedding_summary = await MetricsService(session, nlp).collection_summary(
            collection_id, model="gte-multilingual-base"
        )

    assert tfidf_summary.model == "tfidf"
    assert len(tfidf_summary.queries) == 1
    assert tfidf_summary.queries[0].search_run_id == tfidf_response.search_run_id

    assert embedding_summary.model == "gte-multilingual-base"
    assert len(embedding_summary.queries) == 1
    assert embedding_summary.queries[0].search_run_id == embedding_run_id
    assert embedding_summary.queries[0].average_precision == pytest.approx(1.0)

    async with session_factory() as session:
        compared = await MetricsService(session, nlp).compare(collection_id, ["tfidf", "gte-multilingual-base"])
    assert [s.model for s in compared] == ["tfidf", "gte-multilingual-base"]


@pytest.mark.asyncio
async def test_rerun_all_and_compare_only_reruns_judged_queries(session_factory, collection_with_documents):
    collection_id = collection_with_documents
    nlp = _InProcessNlpClient()

    async with session_factory() as session:
        await IndexingService(session, nlp).reindex_collection_now(collection_id)

    async with session_factory() as session:
        judged_response = await SearchService(session, nlp).search(
            collection_id=collection_id, text="cats domestic animals", top_k=10, model="tfidf"
        )
    cats_doc_id = judged_response.hits[0].document_id

    async with session_factory() as session:
        unjudged_response = await SearchService(session, nlp).search(
            collection_id=collection_id, text="stars and galaxies", top_k=10, model="tfidf"
        )

    async with session_factory() as session:
        from app.infrastructure.repositories.judgments import RelevanceJudgmentRepository
        from app.infrastructure.repositories.queries import QueryRepository
        from app.infrastructure.repositories.search_models import SearchModelRepository

        await RelevanceJudgmentRepository(session).set_judgment(
            query_id=judged_response.query_id, document_id=cats_doc_id, is_relevant=True
        )
        await session.commit()

        tfidf_model = await SearchModelRepository(session).get_by_key("tfidf")
        queries = QueryRepository(session)
        original_unjudged_run = await queries.latest_search_run_for_query(
            unjudged_response.query_id, model_id=tfidf_model.id
        )

    async with session_factory() as session:
        compared = await MetricsService(session, nlp).rerun_all_and_compare(collection_id, ["tfidf"])

    async with session_factory() as session:
        tfidf_model = await SearchModelRepository(session).get_by_key("tfidf")
        queries = QueryRepository(session)
        fresh_judged_run = await queries.latest_search_run_for_query(
            judged_response.query_id, model_id=tfidf_model.id
        )
        unchanged_unjudged_run = await queries.latest_search_run_for_query(
            unjudged_response.query_id, model_id=tfidf_model.id
        )

    assert fresh_judged_run.id != judged_response.search_run_id
    assert unchanged_unjudged_run.id == original_unjudged_run.id

    assert len(compared) == 1
    assert compared[0].model == "tfidf"
    assert [q.query_id for q in compared[0].queries] == [judged_response.query_id]
    assert compared[0].queries[0].search_run_id == fresh_judged_run.id


@pytest.mark.asyncio
async def test_index_job_reports_progress_across_multiple_chunks(session_factory):
    async with session_factory() as session:
        collection = Collection(name="many-docs", language="en")
        session.add(collection)
        await session.flush()
        for i in range(12):
            session.add(
                Document(
                    collection_id=collection.id,
                    title=f"Doc {i}",
                    url=f"https://example.com/{i}",
                    clean_text=f"document number {i} about testing",
                    language="en",
                    char_count=30,
                )
            )
        await session.commit()
        collection_id = collection.id

    nlp = _InProcessNlpClient()
    async with session_factory() as session:
        service = IndexingService(session, nlp)
        job = await service.start_job(collection_id)
        await service.run_job(job.id)
        finished = await service.get_job(job.id)

    assert finished is not None
    assert finished.status == "completed"
    assert finished.documents_total == 24
    assert finished.documents_processed == 24
    assert finished.terms_indexed and finished.terms_indexed > 0


@pytest.mark.asyncio
async def test_deleting_indexed_document_does_not_break_search(session_factory, collection_with_documents):
    collection_id = collection_with_documents
    nlp = _InProcessNlpClient()

    async with session_factory() as session:
        await IndexingService(session, nlp).reindex_collection_now(collection_id)

    async with session_factory() as session:
        first = await SearchService(session, nlp).search(
            collection_id=collection_id, text="cats domestic animals", top_k=10
        )
    cats_id = next(h.document_id for h in first.hits if h.title == "Cats")

    async with session_factory() as session:
        from app.infrastructure.repositories.documents import DocumentRepository

        repo = DocumentRepository(session)
        document = await repo.get(cats_id)
        await repo.delete(document)
        await session.commit()

    async with session_factory() as session:
        second = await SearchService(session, nlp).search(
            collection_id=collection_id, text="cats domestic animals", top_k=10
        )
    assert all(hit.document_id != cats_id for hit in second.hits)


@pytest.mark.asyncio
async def test_editing_document_text_is_stale_until_reindexed(session_factory, collection_with_documents):
    collection_id = collection_with_documents
    nlp = _InProcessNlpClient()

    async with session_factory() as session:
        await IndexingService(session, nlp).reindex_collection_now(collection_id)

    async with session_factory() as session:
        dogs_lookup = await SearchService(session, nlp).search(
            collection_id=collection_id, text="dogs domestic animals", top_k=10
        )
    dogs_id = next(h.document_id for h in dogs_lookup.hits if h.title == "Dogs")

    async with session_factory() as session:
        before = await SearchService(session, nlp).search(
            collection_id=collection_id, text="galaxies universe", top_k=10
        )
    assert dogs_id not in {h.document_id for h in before.hits}

    async with session_factory() as session:
        from app.infrastructure.repositories.documents import DocumentRepository

        repo = DocumentRepository(session)
        document = await repo.get(dogs_id)
        await repo.update(
            document,
            title=document.title,
            url=document.url,
            clean_text="Galaxies fill the universe with stars and cosmic light.",
        )
        await session.commit()

    async with session_factory() as session:
        stale = await SearchService(session, nlp).search(
            collection_id=collection_id, text="galaxies universe", top_k=10
        )
    assert dogs_id not in {h.document_id for h in stale.hits}

    async with session_factory() as session:
        await IndexingService(session, nlp).reindex_collection_now(collection_id)

    async with session_factory() as session:
        fresh = await SearchService(session, nlp).search(
            collection_id=collection_id, text="galaxies universe", top_k=10
        )
    assert dogs_id in {h.document_id for h in fresh.hits}
