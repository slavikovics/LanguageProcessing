from __future__ import annotations

from ips_db import Collection, SearchModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.embedding_padding import pad_to_max_dim
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories.chunk_embeddings import ChunkEmbeddingRepository
from app.infrastructure.repositories.documents import DocumentRepository


class EmbeddingSearchBackend:
    """A dense-embedding backend, parametrized by whichever `search_models`
    row of kind "dense_embedding" is passed to rank() — a future second
    embedding model needs no new backend class, only a new registry row
    (see migrations/versions/0005_search_models.py).

    Ranks a document by its single best-matching chunk (see
    ChunkEmbeddingRepository.nearest_documents / app.domain.indexing.
    chunk_text) rather than one whole-document vector, so a long document
    isn't scored only on however much of it fit in the encoder's truncated
    input.

    There is no discrete "matched term" concept for a dense vector, but
    hits still get a matched-terms list — SearchService computes it
    separately from the indexed TF-IDF vocabulary, independent of which
    backend produced the ranking.
    """

    def __init__(self, session: AsyncSession, nlp_client: NlpServiceClient) -> None:
        self._documents = DocumentRepository(session)
        self._chunk_embeddings = ChunkEmbeddingRepository(session)
        self._nlp = nlp_client

    async def rank(
        self, *, collection: Collection, text: str, model_row: SearchModel
    ) -> list[tuple[int, float]]:
        query_vector = pad_to_max_dim(await self._nlp.embed_query(text))
        document_ids = await self._documents.list_ids_by_collection(collection.id)
        if not document_ids:
            return []
        return await self._chunk_embeddings.nearest_documents(document_ids, model_row.id, query_vector)
