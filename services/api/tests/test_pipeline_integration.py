"""End-to-end check of indexing -> search -> judgments -> metrics wired
together against a real (file-based, throwaway) SQLite database. The only
thing stubbed out is the network hop to nlp-service: `_InProcessNlpClient`
runs the exact same nlp_core functions nlp-service would, in-process, so
this test also verifies that api's HTTP payload shapes match what nlp_core
actually returns.
"""

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
# A handful of stopwords used only by the fixture documents/queries below —
# just enough for "cats"/"cat" not to swamp scoring, without pulling in
# spaCy (nlp-service's real /lemmatize does the actual lemmatization+stopword
# removal; this test only needs *a* stable, deterministic stand-in for it).
_STOPWORDS = {"are", "to", "the", "and"}
_IRREGULAR = {"cats": "cat", "dogs": "dog", "animals": "animal", "galaxies": "galaxy"}


def _fake_lemmatize(text: str) -> list[str]:
    words = _WORD_RE.findall(text.lower())
    return [_IRREGULAR.get(w, w) for w in words if w not in _STOPWORDS]


class _InProcessNlpClient(NlpServiceClient):
    """Same contract as the real HTTP client, computed locally via nlp_core's
    formulas (weighting/metrics — no spaCy needed) instead of an HTTP round
    trip, so this test stays fast and offline while still exercising the
    real TF-IDF/cosine/metrics implementation end to end."""

    def __init__(self) -> None:  # no base_url/timeout needed
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
        precision = metrics.precision_at_k(ranked_ids, relevant, n)
        recall = metrics.recall_at_k(ranked_ids, relevant, n)
        return {
            "retrieved_count": n,
            "relevant_count": len(relevant),
            "precision": precision,
            "recall": recall,
            "f1": metrics.f1_score(precision, recall),
            "precision_at_5": metrics.precision_at_k(ranked_ids, relevant, 5),
            "precision_at_10": metrics.precision_at_k(ranked_ids, relevant, 10),
            "average_precision": metrics.average_precision(ranked_ids, relevant),
            "r_precision": metrics.r_precision(ranked_ids, relevant),
            "curve": metrics.interpolated_precision_recall(ranked_ids, relevant),
        }

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Deterministic 8-dim stand-in for the real dense encoder: a bag-
        of-words hash into fixed buckets, L2-normalized like the real
        sentence-transformers call (normalize_embeddings=True)."""
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

    # SQLite ignores ON DELETE CASCADE unless foreign_keys is turned on per
    # connection — Postgres (production) enforces it unconditionally. Without
    # this, a reindex's document_chunks delete doesn't cascade to
    # document_chunk_embeddings, and SQLite's rowid reuse on the now-empty
    # document_chunks table can collide with those orphaned rows on the next
    # insert (see test_editing_document_text_is_stale_until_reindexed, which
    # reindexes twice).
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):  # noqa: ARG001
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    # Production seeds search_models via migration 0005; these throwaway
    # SQLite databases are built from Base.metadata directly (no alembic),
    # so the same two rows are seeded here instead.
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
    # documents_processed/documents_total count units across every active
    # model's pass (see IndexingService._run) — 3 docs x 2 active models
    # (tfidf + gte-multilingual-base, both seeded active in session_factory).
    assert summary.documents_indexed == 6
    assert summary.terms_indexed > 0

    async with session_factory() as session:
        response = await SearchService(session, nlp).search(
            collection_id=collection_id, text="cats domestic animals", top_k=10
        )
    assert response.hits, "expected at least one ranked document"
    assert response.hits[0].title == "Cats"
    assert "cat" in response.hits[0].matched_terms
    # Astronomy doc shares no vocabulary with the query.
    assert all(hit.title != "Astronomy" for hit in response.hits)

    cats_doc_id = response.hits[0].document_id
    dogs_hit = next((h for h in response.hits if h.title == "Dogs"), None)

    async with session_factory() as session:
        from app.infrastructure.repositories import RelevanceJudgmentRepository

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
    """MetricsService.collection_summary/compare must key off search_runs.
    model_id, not just "the latest run for this query" — two models'
    results for the same query must be evaluated and reported
    independently. The embedding model's search_run/search_results are
    inserted directly via the repositories here (bypassing
    EmbeddingSearchBackend, which issues a pgvector-specific `<=>` SQL
    operator that plain SQLite — used by this test's throwaway DB — has no
    equivalent for; that backend's real behavior is exercised against the
    actual Postgres+pgvector stack instead, not this offline suite)."""
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
        from app.infrastructure.repositories import QueryRepository, RelevanceJudgmentRepository, SearchModelRepository

        embedding_model = await SearchModelRepository(session).get_by_key("gte-multilingual-base")
        queries = QueryRepository(session)
        # Same (collection, text) pools onto the same Query row (query-level
        # pooling stays model-agnostic) — reuse it rather than creating a
        # second Query, exactly like a real search under this model would.
        query_row = await queries.get_or_create_query(collection_id=collection_id, text=tfidf_response.query_text)
        assert query_row.id == tfidf_response.query_id
        embedding_run = await queries.create_search_run(query_id=query_row.id, model_id=embedding_model.id)
        # A different ranking from tfidf's, to prove each summary reads its
        # own model's run rather than "whatever the latest run is."
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
    # Both models scored the same one relevant document at rank 1 in their
    # own ranking, so both should show a perfect AP for this query.
    assert embedding_summary.queries[0].average_precision == pytest.approx(1.0)

    async with session_factory() as session:
        compared = await MetricsService(session, nlp).compare(collection_id, ["tfidf", "gte-multilingual-base"])
    assert [s.model for s in compared] == ["tfidf", "gte-multilingual-base"]


@pytest.mark.asyncio
async def test_index_job_reports_progress_across_multiple_chunks(session_factory):
    """CHUNK_SIZE is 5 — 12 documents should take 3 chunks, and the job
    should end up fully processed regardless of the chunk boundaries."""
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
    # 12 docs x 2 active models (tfidf + gte-multilingual-base) — see the
    # comment in test_full_pipeline_index_search_judge_metrics above.
    assert finished.documents_total == 24
    assert finished.documents_processed == 24
    assert finished.terms_indexed and finished.terms_indexed > 0


@pytest.mark.asyncio
async def test_deleting_indexed_document_does_not_break_search(session_factory, collection_with_documents):
    """Deleting a document cascades to its document_terms/term_weights (FK
    ondelete=CASCADE) and search recomputes document_frequency/N live at
    query time, so the deleted document simply stops being a candidate —
    it must not crash or leave a dangling reference in results."""
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
        from app.infrastructure.repositories import DocumentRepository

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
    """Editing clean_text does not touch document_terms/term_weights — the
    stored vector still reflects the pre-edit text until the collection is
    explicitly reindexed. This documents the current (manual-reindex)
    behavior rather than silently drifting.
    """
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
    # "Dogs" doesn't mention galaxies/universe before the edit.
    assert dogs_id not in {h.document_id for h in before.hits}

    async with session_factory() as session:
        from app.infrastructure.repositories import DocumentRepository

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
    # Stored vector still reflects the OLD text — the edit hasn't been
    # reindexed yet, so it must not appear despite the new text matching.
    assert dogs_id not in {h.document_id for h in stale.hits}

    async with session_factory() as session:
        await IndexingService(session, nlp).reindex_collection_now(collection_id)

    async with session_factory() as session:
        fresh = await SearchService(session, nlp).search(
            collection_id=collection_id, text="galaxies universe", top_k=10
        )
    assert dogs_id in {h.document_id for h in fresh.hits}
