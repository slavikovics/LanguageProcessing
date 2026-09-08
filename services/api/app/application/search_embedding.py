from __future__ import annotations

from ips_db import Collection, SearchModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.embedding_padding import pad_to_max_dim
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories.chunk_embeddings import ChunkEmbeddingRepository
from app.infrastructure.repositories.documents import DocumentRepository


class EmbeddingSearchBackend:

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
