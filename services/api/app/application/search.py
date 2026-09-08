from __future__ import annotations

from ips_db import Collection
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.search_embedding import EmbeddingSearchBackend
from app.application.search_tfidf import TfidfSearchBackend
from app.domain.search import (
    SearchError,
    SearchHit,
    SearchResponse,
    build_search_query_config,
    build_snippet,
)
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories.collections import CollectionRepository
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.index import IndexRepository
from app.infrastructure.repositories.queries import QueryRepository
from app.infrastructure.repositories.search_models import SearchModelRepository
from app.infrastructure.repositories.terms import TermRepository


class SearchService:

    def __init__(self, session: AsyncSession, nlp_client: NlpServiceClient | None = None) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._collections = CollectionRepository(session)
        self._queries = QueryRepository(session)
        self._models = SearchModelRepository(session)
        self._terms = TermRepository(session)
        self._index = IndexRepository(session)
        self._nlp = nlp_client or NlpServiceClient()
        self._backends = {
            "tfidf": TfidfSearchBackend(session, self._nlp),
            "dense_embedding": EmbeddingSearchBackend(session, self._nlp),
        }

    async def _matched_terms_for(
        self, *, collection: Collection, text: str, document_ids: list[int]
    ) -> dict[int, list[str]]:
        if not document_ids:
            return {}
        query_lemmas = await self._nlp.lemmatize(text)
        term_id_by_lemma = await self._terms.get_existing(set(query_lemmas), collection.language)
        if not term_id_by_lemma:
            return {}
        lemma_by_term_id = {term_id: lemma for lemma, term_id in term_id_by_lemma.items()}
        doc_vectors = await self._index.load_document_vectors(document_ids, list(term_id_by_lemma.values()))
        return {
            doc_id: sorted(lemma_by_term_id[term_id] for term_id in vector if term_id in lemma_by_term_id)
            for doc_id, vector in doc_vectors.items()
        }

    async def search(
        self, *, collection_id: int, text: str, top_k: int, model: str = "tfidf"
    ) -> SearchResponse:
        config = build_search_query_config(collection_id=collection_id, text=text, top_k=top_k)

        collection = await self._collections.get(config.collection_id)
        if collection is None:
            raise SearchError(f"collection {config.collection_id} not found")

        model_row = await self._models.get_by_key(model)
        if model_row is None:
            raise SearchError(f"unknown search model '{model}'")
        backend = self._backends.get(model_row.kind)
        if backend is None:
            raise SearchError(f"no backend registered for model kind '{model_row.kind}'")

        ranked = await backend.rank(collection=collection, text=config.text, model_row=model_row)

        top = ranked[: config.top_k]
        documents_by_id = {doc.id: doc for doc in await self._documents.list_by_ids([d for d, _ in top])}
        matched_terms_by_doc = await self._matched_terms_for(
            collection=collection, text=config.text, document_ids=[d for d, _ in top]
        )
        focus_words = config.text.split()

        hits: list[SearchHit] = []
        for rank, (doc_id, score) in enumerate(top, start=1):
            document = documents_by_id.get(doc_id)
            if document is None:
                continue
            hits.append(
                SearchHit(
                    document_id=document.id,
                    title=document.title,
                    url=document.url,
                    fetched_at=document.fetched_at,
                    rank=rank,
                    score=score,
                    snippet=build_snippet(document.clean_text, focus_words),
                    matched_terms=matched_terms_by_doc.get(doc_id, []),
                )
            )

        query_row = await self._queries.get_or_create_query(
            collection_id=config.collection_id, text=config.text
        )
        search_run = await self._queries.create_search_run(query_id=query_row.id, model_id=model_row.id)
        await self._queries.bulk_insert_results(
            search_run.id,
            [(doc_id, rank, score) for rank, (doc_id, score) in enumerate(ranked, start=1)],
        )
        await self._session.commit()

        return SearchResponse(
            query_id=query_row.id,
            search_run_id=search_run.id,
            query_text=config.text,
            model=model_row.key,
            model_label=model_row.label,
            hits=hits,
        )
