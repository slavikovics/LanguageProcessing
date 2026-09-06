from __future__ import annotations

from collections import Counter

from ips_db import Collection, SearchModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories import DocumentRepository, IndexRepository, TermRepository


class TfidfSearchBackend:
    """The original TF-IDF/cosine backend (see docs/ARCHITECTURE.md section
    5, algorithm 3), extracted out of SearchService so it sits behind the
    same rank() contract as EmbeddingSearchBackend — behavior is unchanged
    from before this backend was split out.

    Both the query vector and the stored document vectors are L2-normalized
    (nlp-service's /document-vector always returns a unit vector), so the
    cosine measure r(D,Q) = (D,Q)/(||D||*||Q||) reduces to a plain dot
    product over the terms the two share.
    """

    def __init__(self, session: AsyncSession, nlp_client: NlpServiceClient) -> None:
        self._documents = DocumentRepository(session)
        self._terms = TermRepository(session)
        self._index = IndexRepository(session)
        self._nlp = nlp_client

    async def rank(
        self, *, collection: Collection, text: str, model_row: SearchModel
    ) -> list[tuple[int, float]]:
        query_lemmas = await self._nlp.lemmatize(text)
        term_id_by_lemma = await self._terms.get_existing(set(query_lemmas), collection.language)

        if not term_id_by_lemma:
            return []

        term_ids = list(term_id_by_lemma.values())

        lemma_counts = Counter(query_lemmas)
        query_term_frequencies = {
            str(term_id_by_lemma[lemma]): count
            for lemma, count in lemma_counts.items()
            if lemma in term_id_by_lemma
        }

        document_frequency = await self._index.document_frequency(collection.id, term_ids)
        total_documents = await self._documents.count_by_collection(collection.id)
        idf = await self._nlp.idf_from_frequency(
            {str(k): v for k, v in document_frequency.items()}, total_documents
        )
        query_vector = {
            int(term_id_str): weight
            for term_id_str, weight in (await self._nlp.document_vector(query_term_frequencies, idf)).items()
            if weight != 0.0
        }

        if not query_vector:
            return []

        document_ids = await self._documents.list_ids_by_collection(collection.id)
        doc_vectors = await self._index.load_document_vectors(document_ids, list(query_vector.keys()))

        scored: list[tuple[int, float]] = []
        for doc_id, vector in doc_vectors.items():
            common = vector.keys() & query_vector.keys()
            if not common:
                continue
            score = sum(vector[term_id] * query_vector[term_id] for term_id in common)
            scored.append((doc_id, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored
