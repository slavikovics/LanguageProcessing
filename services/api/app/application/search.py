from __future__ import annotations

from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.search import (
    SearchError,
    SearchHit,
    SearchResponse,
    build_search_query_config,
    build_snippet,
)
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories import (
    CollectionRepository,
    DocumentRepository,
    IndexRepository,
    QueryRepository,
    TermRepository,
)


class SearchService:
    """Builds the ПОЗ (поисковый образ запроса), scores it against every
    indexed document in the collection by cosine similarity, and persists
    the run — see docs/ARCHITECTURE.md section 5 (algorithm 3).

    Both the query vector and the stored document vectors are L2-normalized
    (nlp-service's /document-vector always returns a unit vector), so the
    cosine measure r(D,Q) = (D,Q)/(||D||*||Q||) reduces to a plain dot
    product over the terms the two share — no need to load a document's full
    vector, only the rows for terms present in the query.
    """

    def __init__(self, session: AsyncSession, nlp_client: NlpServiceClient | None = None) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._collections = CollectionRepository(session)
        self._terms = TermRepository(session)
        self._index = IndexRepository(session)
        self._queries = QueryRepository(session)
        self._nlp = nlp_client or NlpServiceClient()

    async def search(self, *, collection_id: int, text: str, top_k: int) -> SearchResponse:
        config = build_search_query_config(collection_id=collection_id, text=text, top_k=top_k)

        collection = await self._collections.get(config.collection_id)
        if collection is None:
            raise SearchError(f"collection {config.collection_id} not found")

        query_lemmas = await self._nlp.lemmatize(config.text)
        term_id_by_lemma = await self._terms.get_existing(set(query_lemmas), collection.language)

        ranked: list[tuple[int, float, set[int]]] = []
        if term_id_by_lemma:
            lemma_by_term_id = {term_id: lemma for lemma, term_id in term_id_by_lemma.items()}
            term_ids = list(term_id_by_lemma.values())

            lemma_counts = Counter(query_lemmas)
            query_term_frequencies = {
                str(term_id_by_lemma[lemma]): count
                for lemma, count in lemma_counts.items()
                if lemma in term_id_by_lemma
            }

            document_frequency = await self._index.document_frequency(config.collection_id, term_ids)
            total_documents = await self._documents.count_by_collection(config.collection_id)
            idf = await self._nlp.idf_from_frequency(
                {str(k): v for k, v in document_frequency.items()}, total_documents
            )
            query_vector = {
                int(term_id_str): weight
                for term_id_str, weight in (
                    await self._nlp.document_vector(query_term_frequencies, idf)
                ).items()
                if weight != 0.0
            }

            if query_vector:
                document_ids = await self._documents.list_ids_by_collection(config.collection_id)
                doc_vectors = await self._index.load_document_vectors(
                    document_ids, list(query_vector.keys())
                )
                for doc_id, vector in doc_vectors.items():
                    common = vector.keys() & query_vector.keys()
                    if not common:
                        continue
                    score = sum(vector[term_id] * query_vector[term_id] for term_id in common)
                    ranked.append((doc_id, score, common))
                ranked.sort(key=lambda item: item[1], reverse=True)
        else:
            lemma_by_term_id = {}

        top = ranked[: config.top_k]
        documents_by_id = {doc.id: doc for doc in await self._documents.list_by_ids([d for d, _, _ in top])}
        focus_words = config.text.split()

        hits: list[SearchHit] = []
        for rank, (doc_id, score, common_term_ids) in enumerate(top, start=1):
            document = documents_by_id.get(doc_id)
            if document is None:
                continue
            matched_terms = sorted(
                lemma_by_term_id[term_id] for term_id in common_term_ids if term_id in lemma_by_term_id
            )
            hits.append(
                SearchHit(
                    document_id=document.id,
                    title=document.title,
                    url=document.url,
                    fetched_at=document.fetched_at,
                    rank=rank,
                    score=score,
                    snippet=build_snippet(document.clean_text, focus_words),
                    matched_terms=matched_terms,
                )
            )

        query_row = await self._queries.create_query(collection_id=config.collection_id, text=config.text)
        search_run = await self._queries.create_search_run(query_id=query_row.id)
        await self._queries.bulk_insert_results(
            search_run.id, [(hit.document_id, hit.rank, hit.score) for hit in hits]
        )
        await self._session.commit()

        return SearchResponse(
            query_id=query_row.id,
            search_run_id=search_run.id,
            query_text=config.text,
            hits=hits,
        )
