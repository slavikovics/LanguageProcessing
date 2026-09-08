from __future__ import annotations

from ips_db import DocumentChunk, DocumentChunkEmbedding
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession


class ChunkEmbeddingRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_write(self, rows: list[dict[str, object]]) -> None:
        if not rows:
            return
        await self._session.execute(insert(DocumentChunkEmbedding), rows)

    async def get_first_chunk_vectors(
        self, document_ids: list[int], search_model_id: int
    ) -> dict[int, list[float]]:
        if not document_ids:
            return {}
        result = await self._session.execute(
            select(DocumentChunk.document_id, DocumentChunkEmbedding.embedding)
            .join(DocumentChunkEmbedding, DocumentChunkEmbedding.chunk_id == DocumentChunk.id)
            .where(
                DocumentChunkEmbedding.search_model_id == search_model_id,
                DocumentChunk.chunk_index == 0,
                DocumentChunk.document_id.in_(document_ids),
            )
        )
        return {document_id: [float(x) for x in embedding] for document_id, embedding in result.all()}

    async def nearest_documents(
        self, document_ids: list[int], search_model_id: int, query_vector: list[float]
    ) -> list[tuple[int, float]]:
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
