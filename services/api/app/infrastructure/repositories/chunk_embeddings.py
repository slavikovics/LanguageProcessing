from __future__ import annotations

from ips_db import DocumentChunk, DocumentChunkEmbedding
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession


class ChunkEmbeddingRepository:
    """Writes/reads document_chunk_embeddings — the dense-model counterpart
    to IndexRepository's term_weights, one row per chunk. Vectors arrive
    already zero-padded to MAX_EMBEDDING_DIM by the caller."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_write(self, rows: list[dict[str, object]]) -> None:
        """rows: [{chunk_id, search_model_id, embedding}, ...]."""
        if not rows:
            return
        await self._session.execute(insert(DocumentChunkEmbedding), rows)

    async def nearest_documents(
        self, document_ids: list[int], search_model_id: int, query_vector: list[float]
    ) -> list[tuple[int, float]]:
        """Every document with at least one chunk vector under this model,
        ranked by its best-matching chunk's cosine similarity, best first —
        unlimited, so rank-sensitive metrics stay correct. pgvector's `<=>`
        returns cosine distance, so we return 1 - distance to match TF-IDF's
        higher-is-better score scale."""
        if not document_ids:
            return []
        similarity = (1.0 - DocumentChunkEmbedding.embedding.cosine_distance(query_vector)).label(
            "similarity"
        )
        best_similarity = func.max(similarity)
        result = await self._session.execute(
            select(DocumentChunk.document_id, best_similarity)
            .join(DocumentChunkEmbedding, DocumentChunkEmbedding.chunk_id == DocumentChunk.id)
            .where(
                DocumentChunkEmbedding.search_model_id == search_model_id,
                DocumentChunk.document_id.in_(document_ids),
            )
            .group_by(DocumentChunk.document_id)
            .order_by(best_similarity.desc())
        )
        return [(doc_id, score) for doc_id, score in result.all()]
