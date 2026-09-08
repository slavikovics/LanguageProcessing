from __future__ import annotations

import datetime as dt

from ips_db import Collection, IndexJob, SearchModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.indexing import IndexingCancelled, IndexingError, IndexingSummary, chunk_text
from app.infrastructure.embedding_padding import pad_to_max_dim
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories.chunk_embeddings import ChunkEmbeddingRepository
from app.infrastructure.repositories.chunks import ChunkRepository
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.index import IndexRepository
from app.infrastructure.repositories.index_jobs import IndexJobRepository
from app.infrastructure.repositories.search_models import SearchModelRepository
from app.infrastructure.repositories.terms import TermRepository

CHUNK_SIZE = 32
EMBEDDING_CHUNK_SIZE = 16

_ACTIVE_STATUSES = {"pending", "running"}


class IndexJobNotFound(Exception):
    pass


class IndexingService:

    def __init__(self, session: AsyncSession, nlp_client: NlpServiceClient | None = None) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._terms = TermRepository(session)
        self._index = IndexRepository(session)
        self._chunks = ChunkRepository(session)
        self._chunk_embeddings = ChunkEmbeddingRepository(session)
        self._models = SearchModelRepository(session)
        self._jobs = IndexJobRepository(session)
        self._nlp = nlp_client or NlpServiceClient()

    async def start_job(self, collection_id: int) -> IndexJob:
        collection = await self._session.get(Collection, collection_id)
        if collection is None:
            raise IndexingError(f"collection {collection_id} not found")

        has_documents = await self._documents.count_by_collection(collection_id)
        if has_documents == 0:
            raise IndexingError("collection has no documents to index")

        job = await self._jobs.create(collection_id=collection_id)
        await self._session.commit()
        return job

    async def get_job(self, job_id: int) -> IndexJob | None:
        return await self._jobs.get(job_id)

    async def get_latest_job(self, collection_id: int) -> IndexJob | None:
        return await self._jobs.latest_for_collection(collection_id)

    async def run_job(self, job_id: int) -> None:
        job = await self._jobs.get(job_id)
        if job is None:
            return
        try:
            await self._run(job)
        except IndexingCancelled:
            pass
        except Exception as exc:
            message = str(exc) or type(exc).__name__
            await self._jobs.mark_failed(job_id, error_message=f"{type(exc).__name__}: {message}")

    async def cancel_job(self, job_id: int) -> None:
        job = await self._jobs.get(job_id)
        if job is None:
            raise IndexJobNotFound(f"index job {job_id} not found")
        if job.status not in _ACTIVE_STATUSES:
            raise IndexingError(f"index job {job_id} is already {job.status}")
        await self._jobs.request_cancel(job_id)
        job.status = "cancelled"
        job.finished_at = dt.datetime.utcnow()

    async def _ensure_not_cancelled(self, job_id: int) -> None:
        if await self._jobs.get_status(job_id) == "cancelled":
            raise IndexingCancelled()

    async def _run(self, job: IndexJob) -> None:
        collection = await self._session.get(Collection, job.collection_id)
        if collection is None:
            raise IndexingError(f"collection {job.collection_id} not found")

        documents = await self._documents.list_all_by_collection(job.collection_id)
        document_ids = [doc.id for doc in documents]

        active_models = await self._models.list_active()
        embedding_models = [m for m in active_models if m.kind == "dense_embedding"]

        total_units = len(documents) * (1 + len(embedding_models))
        started = await self._jobs.mark_running(job.id, documents_total=total_units)
        if not started:
            raise IndexingCancelled()

        processed, terms_indexed = await self._run_tfidf_pass(job, collection, documents)
        await self._ensure_not_cancelled(job.id)
        for model_row in embedding_models:
            processed = await self._run_embedding_pass(job, documents, document_ids, model_row, processed)

        await self._session.commit()
        await self._jobs.mark_completed(job.id, terms_indexed=terms_indexed)

    async def _run_tfidf_pass(self, job: IndexJob, collection: Collection, documents: list) -> tuple[int, int]:
        lemma_lists: list[list[str]] = []
        processed = 0
        for start in range(0, len(documents), CHUNK_SIZE):
            chunk = documents[start : start + CHUNK_SIZE]
            chunk_lemmas = await self._nlp.lemmatize_batch([doc.clean_text for doc in chunk])
            lemma_lists.extend(chunk_lemmas)
            processed = len(lemma_lists)
            await self._jobs.update_progress(job.id, documents_processed=processed)
            await self._ensure_not_cancelled(job.id)

        indexed = await self._nlp.index(lemma_lists)
        idf: dict[str, float] = indexed["idf"]
        term_frequencies: list[dict[str, int]] = indexed["term_frequencies"]
        vectors: list[dict[str, float]] = indexed["vectors"]

        term_ids = await self._terms.get_or_create_many(set(idf.keys()), collection.language)

        document_ids = [doc.id for doc in documents]
        await self._index.clear_for_documents(document_ids)

        document_term_rows: list[dict[str, int]] = []
        term_weight_rows: list[dict[str, object]] = []
        for document, freqs, vector in zip(documents, term_frequencies, vectors):
            for lemma, tf in freqs.items():
                term_id = term_ids.get(lemma)
                if term_id is None:
                    continue
                document_term_rows.append({"document_id": document.id, "term_id": term_id, "tf": tf})
            for lemma, weight in vector.items():
                term_id = term_ids.get(lemma)
                if term_id is None or weight == 0.0:
                    continue
                term_weight_rows.append(
                    {"document_id": document.id, "term_id": term_id, "weight": weight}
                )

        await self._index.bulk_write(document_term_rows, term_weight_rows)
        return processed, len(term_ids)

    async def _run_embedding_pass(
        self,
        job: IndexJob,
        documents: list,
        document_ids: list[int],
        model_row: SearchModel,
        processed: int,
    ) -> int:
        await self._chunks.clear_for_documents(document_ids)
        for start in range(0, len(documents), EMBEDDING_CHUNK_SIZE):
            batch = documents[start : start + EMBEDDING_CHUNK_SIZE]
            chunk_rows = [
                {"document_id": document.id, "chunk_index": index, "text": text}
                for document in batch
                for index, text in enumerate(chunk_text(document.clean_text))
            ]
            if chunk_rows:
                chunks = await self._chunks.bulk_create(chunk_rows)
                vectors = await self._nlp.embed_documents([c.text for c in chunks])
                embedding_rows = [
                    {
                        "chunk_id": db_chunk.id,
                        "search_model_id": model_row.id,
                        "embedding": pad_to_max_dim(vector),
                    }
                    for db_chunk, vector in zip(chunks, vectors)
                ]
                await self._chunk_embeddings.bulk_write(embedding_rows)
            processed += len(batch)
            await self._jobs.update_progress(job.id, documents_processed=processed)
            await self._ensure_not_cancelled(job.id)
        return processed

    async def reindex_collection_now(self, collection_id: int) -> IndexingSummary:
        job = await self.start_job(collection_id)
        await self.run_job(job.id)
        finished = await self._jobs.get(job.id)
        if finished is None or finished.status != "completed":
            error = finished.error_message if finished else "index job vanished"
            raise IndexingError(error or "indexing failed")
        return IndexingSummary(
            collection_id=collection_id,
            documents_indexed=finished.documents_processed,
            terms_indexed=finished.terms_indexed or 0,
        )
