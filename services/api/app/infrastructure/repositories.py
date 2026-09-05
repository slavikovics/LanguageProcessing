from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ips_db import (
    Collection,
    CrawlJob,
    CrawlSeed,
    CrawlUrl,
    Document,
    DocumentEmbedding,
    DocumentTerm,
    IndexJob,
    MetricResult,
    Query,
    RelevanceJudgment,
    SearchModel,
    SearchResult,
    SearchRun,
    Term,
    TermWeight,
)

from app.domain.enums import CrawlJobStatus, CrawlUrlStatus, IndexJobStatus


class CollectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str, language: str) -> Collection:
        collection = Collection(name=name, language=language)
        self._session.add(collection)
        await self._session.flush()
        return collection

    async def get(self, collection_id: int) -> Collection | None:
        return await self._session.get(Collection, collection_id)

    async def list(self) -> list[Collection]:
        result = await self._session.execute(select(Collection).order_by(Collection.id))
        return list(result.scalars().all())

    async def list_with_document_counts(self) -> list[tuple[Collection, int]]:
        result = await self._session.execute(
            select(Collection, func.count(Document.id))
            .outerjoin(Document, Document.collection_id == Collection.id)
            .group_by(Collection.id)
            .order_by(Collection.id)
        )
        return [(collection, count) for collection, count in result.all()]

    async def touch_documents_changed(self, collection_id: int) -> None:
        """Marks the collection's document set as changed *now* — compared
        against the latest IndexJob's finished_at to flag a stale index in
        the UI. Called on every document create/update/delete/refresh.

        Uses fetch-then-mutate (not a bare Core UPDATE) so an already
        -loaded Collection object in this same session's identity map picks
        up the new value immediately instead of staying stale — see the
        IndexJobRepository fix for why a raw UPDATE isn't safe here.
        """
        collection = await self._session.get(Collection, collection_id)
        if collection is not None:
            collection.documents_changed_at = dt.datetime.utcnow()
            await self._session.flush()


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_collection(self, collection_id: int, *, limit: int = 50, offset: int = 0) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.collection_id == collection_id)
            .order_by(Document.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get(self, document_id: int) -> Document | None:
        return await self._session.get(Document, document_id)

    async def count_by_collection(self, collection_id: int) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Document).where(Document.collection_id == collection_id)
        )
        return int(result.scalar_one())

    async def list_all_by_collection(self, collection_id: int) -> list[Document]:
        result = await self._session.execute(
            select(Document).where(Document.collection_id == collection_id).order_by(Document.id)
        )
        return list(result.scalars().all())

    async def list_by_ids(self, document_ids: list[int]) -> list[Document]:
        if not document_ids:
            return []
        result = await self._session.execute(select(Document).where(Document.id.in_(document_ids)))
        return list(result.scalars().all())

    async def list_ids_by_collection(self, collection_id: int) -> list[int]:
        result = await self._session.execute(
            select(Document.id).where(Document.collection_id == collection_id)
        )
        return [row[0] for row in result.all()]

    async def create(
        self, *, collection_id: int, title: str, url: str | None, clean_text: str, language: str
    ) -> Document:
        document = Document(
            collection_id=collection_id,
            title=title,
            url=url,
            clean_text=clean_text,
            language=language,
            char_count=len(clean_text),
        )
        self._session.add(document)
        await self._session.flush()
        return document

    async def update(
        self, document: Document, *, title: str, url: str | None, clean_text: str
    ) -> Document:
        document.title = title
        document.url = url
        document.clean_text = clean_text
        document.char_count = len(clean_text)
        await self._session.flush()
        return document

    async def delete(self, document: Document) -> None:
        await self._session.delete(document)

    async def get_by_url(self, collection_id: int, url: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.collection_id == collection_id, Document.url == url)
        )
        return result.scalars().first()

    async def list_urls_by_collection(self, collection_id: int) -> list[str]:
        result = await self._session.execute(
            select(Document.url).where(
                Document.collection_id == collection_id, Document.url.is_not(None)
            )
        )
        return [row[0] for row in result.all()]

    async def delete_all_by_collection(self, collection_id: int) -> None:
        """Bulk-deletes every document in the collection. Relies on the DB-
        level ON DELETE CASCADE from document_terms/term_weights/
        search_results/relevance_judgments (see migration 0001) to clear the
        built index and any qrels/results pointing at these documents —
        used by CrawlJobService.run_collection_crawl to rebuild from
        scratch on every recrawl."""
        await self._session.execute(delete(Document).where(Document.collection_id == collection_id))


class TermRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_existing(self, lemmas: set[str], language: str) -> dict[str, int]:
        """Lemma -> term_id for the subset of `lemmas` already indexed in
        this language; unknown terms are simply absent (they contribute
        nothing to a query vector — the collection's vocabulary doesn't
        know them yet)."""
        if not lemmas:
            return {}
        result = await self._session.execute(
            select(Term).where(Term.language == language, Term.lemma.in_(lemmas))
        )
        return {term.lemma: term.id for term in result.scalars().all()}

    async def get_or_create_many(self, lemmas: set[str], language: str) -> dict[str, int]:
        """Returns lemma -> term_id for every lemma, creating rows for the
        ones not seen yet in this language."""
        if not lemmas:
            return {}
        result = await self._session.execute(
            select(Term).where(Term.language == language, Term.lemma.in_(lemmas))
        )
        term_ids = {term.lemma: term.id for term in result.scalars().all()}

        missing = lemmas - term_ids.keys()
        if missing:
            new_terms = [Term(lemma=lemma, language=language) for lemma in missing]
            self._session.add_all(new_terms)
            await self._session.flush()
            term_ids.update({term.lemma: term.id for term in new_terms})
        return term_ids


class IndexRepository:
    """Writes document_terms/term_weights — the persisted vector of the
    document (`GetDocumentVector` from the methodology)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def clear_for_documents(self, document_ids: list[int]) -> None:
        if not document_ids:
            return
        await self._session.execute(
            delete(DocumentTerm).where(DocumentTerm.document_id.in_(document_ids))
        )
        await self._session.execute(
            delete(TermWeight).where(TermWeight.document_id.in_(document_ids))
        )

    async def bulk_write(
        self, document_terms: list[dict[str, int]], term_weights: list[dict[str, object]]
    ) -> None:
        if document_terms:
            await self._session.execute(insert(DocumentTerm), document_terms)
        if term_weights:
            await self._session.execute(insert(TermWeight), term_weights)

    async def load_document_vectors(
        self, document_ids: list[int], term_ids: list[int]
    ) -> dict[int, dict[int, float]]:
        """document_id -> {term_id: weight}, restricted to the given terms —
        enough to score cosine similarity since stored vectors are already
        L2-normalized, so only the shared-term dot product is needed."""
        if not document_ids or not term_ids:
            return {}
        result = await self._session.execute(
            select(TermWeight.document_id, TermWeight.term_id, TermWeight.weight).where(
                TermWeight.document_id.in_(document_ids), TermWeight.term_id.in_(term_ids)
            )
        )
        vectors: dict[int, dict[int, float]] = {}
        for document_id, term_id, weight in result.all():
            vectors.setdefault(document_id, {})[term_id] = weight
        return vectors

    async def document_frequency(self, collection_id: int, term_ids: list[int]) -> dict[int, int]:
        """P_i restricted to a collection: number of documents in it that
        contain each term, straight from document_terms + documents — the
        source of IDF per docs/ARCHITECTURE.md section 4."""
        if not term_ids:
            return {}
        result = await self._session.execute(
            select(DocumentTerm.term_id, func.count(func.distinct(DocumentTerm.document_id)))
            .join(Document, Document.id == DocumentTerm.document_id)
            .where(Document.collection_id == collection_id, DocumentTerm.term_id.in_(term_ids))
            .group_by(DocumentTerm.term_id)
        )
        return {term_id: count for term_id, count in result.all()}

    async def indexed_term_count(self, document_ids: list[int]) -> int:
        if not document_ids:
            return 0
        result = await self._session.execute(
            select(func.count(func.distinct(TermWeight.term_id))).where(
                TermWeight.document_id.in_(document_ids)
            )
        )
        return int(result.scalar_one())


class SearchModelRepository:
    """Reads the search_models registry seeded by migrations (see
    migrations/versions/0005_search_models.py) — the schema never changes
    when a new model is added, only a new seeded row."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(self, key: str) -> SearchModel | None:
        result = await self._session.execute(select(SearchModel).where(SearchModel.key == key))
        return result.scalars().first()

    async def list_active(self) -> list[SearchModel]:
        result = await self._session.execute(
            select(SearchModel).where(SearchModel.is_active.is_(True)).order_by(SearchModel.id)
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[SearchModel]:
        result = await self._session.execute(select(SearchModel).order_by(SearchModel.id))
        return list(result.scalars().all())


class EmbeddingRepository:
    """Writes/reads document_embeddings — the dense-model counterpart to
    IndexRepository's term_weights. Vectors are stored zero-padded to
    MAX_EMBEDDING_DIM by the caller (see embedding_padding.pad_to_max_dim)
    before reaching this repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def clear_for_documents(self, document_ids: list[int], search_model_id: int) -> None:
        if not document_ids:
            return
        await self._session.execute(
            delete(DocumentEmbedding).where(
                DocumentEmbedding.search_model_id == search_model_id,
                DocumentEmbedding.document_id.in_(document_ids),
            )
        )

    async def bulk_write(self, rows: list[dict[str, object]]) -> None:
        """rows: [{document_id, search_model_id, embedding}, ...]."""
        if not rows:
            return
        await self._session.execute(insert(DocumentEmbedding), rows)

    async def nearest(
        self, document_ids: list[int], search_model_id: int, query_vector: list[float]
    ) -> list[tuple[int, float]]:
        """Every document in `document_ids` that has a stored vector under
        this model, ranked by cosine similarity, best first — not limited,
        so rank-sensitive metrics (AP/R-precision/the curve) stay correct
        the same way TF-IDF's full ranking does. pgvector's `<=>` operator
        returns cosine *distance*; we return `1 - distance` so the score
        scale matches TF-IDF's dot product (higher is better)."""
        if not document_ids:
            return []
        distance = DocumentEmbedding.embedding.cosine_distance(query_vector)
        result = await self._session.execute(
            select(DocumentEmbedding.document_id, distance.label("distance"))
            .where(
                DocumentEmbedding.search_model_id == search_model_id,
                DocumentEmbedding.document_id.in_(document_ids),
            )
            .order_by(distance)
        )
        return [(doc_id, 1.0 - dist) for doc_id, dist in result.all()]


class IndexJobRepository:
    """Tracks indexing progress the same way CrawlJobRepository tracks
    crawling — a DB row api.interface.routers.index_jobs polls/pushes so the
    frontend can show a live progress bar (docs/PROJECT_PLAN.md, 3.1 pattern
    reused for the indexing pipeline)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, collection_id: int) -> IndexJob:
        job = IndexJob(collection_id=collection_id, status=IndexJobStatus.PENDING.value)
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: int) -> IndexJob | None:
        return await self._session.get(IndexJob, job_id)

    async def latest_for_collection(self, collection_id: int) -> IndexJob | None:
        result = await self._session.execute(
            select(IndexJob)
            .where(IndexJob.collection_id == collection_id)
            .order_by(IndexJob.id.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def mark_running(self, job_id: int, *, documents_total: int) -> None:
        job = await self._session.get(IndexJob, job_id)
        if job is None:
            return
        job.status = IndexJobStatus.RUNNING.value
        job.documents_total = documents_total
        job.started_at = dt.datetime.utcnow()
        await self._session.commit()

    async def update_progress(self, job_id: int, *, documents_processed: int) -> None:
        job = await self._session.get(IndexJob, job_id)
        if job is None:
            return
        job.documents_processed = documents_processed
        await self._session.commit()

    async def mark_completed(self, job_id: int, *, terms_indexed: int) -> None:
        job = await self._session.get(IndexJob, job_id)
        if job is None:
            return
        job.status = IndexJobStatus.COMPLETED.value
        job.terms_indexed = terms_indexed
        job.finished_at = dt.datetime.utcnow()
        await self._session.commit()

    async def mark_failed(self, job_id: int, *, error_message: str) -> None:
        job = await self._session.get(IndexJob, job_id)
        if job is None:
            return
        job.status = IndexJobStatus.FAILED.value
        job.error_message = error_message[:1000]
        job.finished_at = dt.datetime.utcnow()
        await self._session.commit()

    async def delete_all_by_collection(self, collection_id: int) -> None:
        await self._session.execute(delete(IndexJob).where(IndexJob.collection_id == collection_id))


class QueryRepository:
    """Persists Query/SearchRun/SearchResult — the audit trail a search
    leaves behind, which relevance_judgments and metric_results build on."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_query(self, *, collection_id: int, text: str) -> Query:
        """Reuses the existing Query row for this exact (collection, text)
        pair rather than inserting a new one per search: relevance
        judgments are keyed by query_id, so re-running the same query text
        (e.g. with a larger top_k to look further down the ranking) has to
        land on the same query for those judgments to accumulate into one
        qrel set — otherwise the "relevant" universe a run is scored
        against can never extend past that one run's own results, which
        makes recall trivially 1.0 whenever anything is marked relevant."""
        result = await self._session.execute(
            select(Query).where(Query.collection_id == collection_id, Query.text == text)
        )
        existing = result.scalars().first()
        if existing is not None:
            return existing
        query = Query(collection_id=collection_id, text=text)
        self._session.add(query)
        await self._session.flush()
        return query

    async def get_query(self, query_id: int) -> Query | None:
        return await self._session.get(Query, query_id)

    async def list_queries_by_collection(self, collection_id: int) -> list[Query]:
        result = await self._session.execute(
            select(Query).where(Query.collection_id == collection_id).order_by(Query.id.desc())
        )
        return list(result.scalars().all())

    async def create_search_run(self, *, query_id: int, model_id: int) -> SearchRun:
        run = SearchRun(query_id=query_id, model_id=model_id)
        self._session.add(run)
        await self._session.flush()
        return run

    async def get_search_run(self, search_run_id: int) -> SearchRun | None:
        return await self._session.get(SearchRun, search_run_id)

    async def latest_search_run_for_query(self, query_id: int, *, model_id: int) -> SearchRun | None:
        result = await self._session.execute(
            select(SearchRun)
            .where(SearchRun.query_id == query_id, SearchRun.model_id == model_id)
            .order_by(SearchRun.id.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def bulk_insert_results(
        self, search_run_id: int, hits: list[tuple[int, int, float]]
    ) -> None:
        """hits: list of (document_id, rank, score)."""
        if not hits:
            return
        rows = [
            {"search_run_id": search_run_id, "document_id": doc_id, "rank": rank, "score": score}
            for doc_id, rank, score in hits
        ]
        await self._session.execute(insert(SearchResult), rows)

    async def list_results(self, search_run_id: int) -> list[SearchResult]:
        result = await self._session.execute(
            select(SearchResult)
            .where(SearchResult.search_run_id == search_run_id)
            .order_by(SearchResult.rank)
        )
        return list(result.scalars().all())


class RelevanceJudgmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set_judgment(self, *, query_id: int, document_id: int, is_relevant: bool) -> None:
        existing = await self._session.get(RelevanceJudgment, (query_id, document_id))
        if existing is not None:
            existing.is_relevant = is_relevant
        else:
            self._session.add(
                RelevanceJudgment(query_id=query_id, document_id=document_id, is_relevant=is_relevant)
            )
        await self._session.flush()

    async def clear_judgment(self, *, query_id: int, document_id: int) -> None:
        existing = await self._session.get(RelevanceJudgment, (query_id, document_id))
        if existing is not None:
            await self._session.delete(existing)
            await self._session.flush()

    async def relevant_document_ids(self, query_id: int) -> set[int]:
        result = await self._session.execute(
            select(RelevanceJudgment.document_id).where(
                RelevanceJudgment.query_id == query_id, RelevanceJudgment.is_relevant.is_(True)
            )
        )
        return {row[0] for row in result.all()}

    async def list_for_query(self, query_id: int) -> list[RelevanceJudgment]:
        result = await self._session.execute(
            select(RelevanceJudgment).where(RelevanceJudgment.query_id == query_id)
        )
        return list(result.scalars().all())


class MetricResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_run(self, search_run_id: int, metrics: dict[str, float]) -> None:
        await self._session.execute(
            delete(MetricResult).where(MetricResult.search_run_id == search_run_id)
        )
        if metrics:
            rows = [
                {"search_run_id": search_run_id, "metric_name": name, "value": value}
                for name, value in metrics.items()
            ]
            await self._session.execute(insert(MetricResult), rows)

    async def list_for_run(self, search_run_id: int) -> list[MetricResult]:
        result = await self._session.execute(
            select(MetricResult).where(MetricResult.search_run_id == search_run_id)
        )
        return list(result.scalars().all())


class CrawlSeedRepository:
    """CRUD for the persisted, per-collection crawl address list — the
    source CrawlJobService.run_collection_crawl reads to spawn one CrawlJob
    per seed."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_collection(self, collection_id: int) -> list[CrawlSeed]:
        result = await self._session.execute(
            select(CrawlSeed).where(CrawlSeed.collection_id == collection_id).order_by(CrawlSeed.id)
        )
        return list(result.scalars().all())

    async def get(self, seed_id: int) -> CrawlSeed | None:
        return await self._session.get(CrawlSeed, seed_id)

    async def count_by_collection(self, collection_id: int) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(CrawlSeed).where(CrawlSeed.collection_id == collection_id)
        )
        return int(result.scalar_one())

    async def create(
        self,
        *,
        collection_id: int,
        url: str,
        max_documents: int,
        max_depth: int,
        same_domain_only: bool,
    ) -> CrawlSeed:
        seed = CrawlSeed(
            collection_id=collection_id,
            url=url,
            max_documents=max_documents,
            max_depth=max_depth,
            same_domain_only=same_domain_only,
        )
        self._session.add(seed)
        await self._session.flush()
        return seed

    async def update(
        self, seed: CrawlSeed, *, url: str, max_documents: int, max_depth: int, same_domain_only: bool
    ) -> CrawlSeed:
        seed.url = url
        seed.max_documents = max_documents
        seed.max_depth = max_depth
        seed.same_domain_only = same_domain_only
        await self._session.flush()
        return seed

    async def delete(self, seed: CrawlSeed) -> None:
        await self._session.delete(seed)


class CrawlJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        collection_id: int,
        seed_urls: list[str],
        max_documents: int,
        max_depth: int,
        mode: str = "crawl",
        allowed_domain: str | None = None,
    ) -> CrawlJob:
        job = CrawlJob(
            collection_id=collection_id,
            seed_urls=seed_urls,
            max_documents=max_documents,
            max_depth=max_depth,
            mode=mode,
            allowed_domain=allowed_domain,
            status=CrawlJobStatus.PENDING.value,
            urls_queued=len(seed_urls),
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: int) -> CrawlJob | None:
        return await self._session.get(CrawlJob, job_id)

    async def list(self, *, collection_id: int | None = None, limit: int = 50) -> list[CrawlJob]:
        query = select(CrawlJob).order_by(CrawlJob.id.desc()).limit(limit)
        if collection_id is not None:
            query = query.where(CrawlJob.collection_id == collection_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_pending(self) -> list[CrawlJob]:
        result = await self._session.execute(
            select(CrawlJob).where(CrawlJob.status == CrawlJobStatus.PENDING.value)
        )
        return list(result.scalars().all())

    async def mark_status(
        self,
        job_id: int,
        status: CrawlJobStatus,
        *,
        error_message: str | None = None,
    ) -> None:
        values: dict[str, object] = {"status": status.value}
        if status == CrawlJobStatus.RUNNING:
            values["started_at"] = dt.datetime.utcnow()
        if status.is_terminal:
            values["finished_at"] = dt.datetime.utcnow()
        if error_message is not None:
            values["error_message"] = error_message
        await self._session.execute(update(CrawlJob).where(CrawlJob.id == job_id).values(**values))
        await self._session.commit()


class CrawlUrlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_enqueue(
        self, job_id: int, urls: list[str], *, depth: int, discovered_from_id: int | None = None
    ) -> list[CrawlUrl]:
        entries = [
            CrawlUrl(
                job_id=job_id,
                url=url,
                depth=depth,
                status=CrawlUrlStatus.QUEUED.value,
                discovered_from_id=discovered_from_id,
            )
            for url in urls
        ]
        self._session.add_all(entries)
        await self._session.flush()
        return entries

    # Only URLs that were actually fetched and evaluated as a document
    # candidate — succeeded, failed to fetch, or were fetched but rejected
    # (too short, duplicate). Excludes "queued"/"fetching" (not resolved
    # yet) and "blocked" (robots.txt disallowed it before it was ever
    # fetched, so it was never a candidate at all).
    _DOCUMENT_CANDIDATE_STATUSES = (
        CrawlUrlStatus.SUCCESS.value,
        CrawlUrlStatus.FAILED.value,
        CrawlUrlStatus.SKIPPED.value,
    )

    async def list_by_job(self, job_id: int, *, limit: int = 50) -> list[CrawlUrl]:
        result = await self._session.execute(
            select(CrawlUrl)
            .where(
                CrawlUrl.job_id == job_id,
                CrawlUrl.status.in_(self._DOCUMENT_CANDIDATE_STATUSES),
            )
            .order_by(CrawlUrl.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
