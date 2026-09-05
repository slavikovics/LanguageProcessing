from __future__ import annotations

from ips_db import Collection, SearchModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.embedding_padding import pad_to_max_dim
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories import DocumentRepository, EmbeddingRepository


class EmbeddingSearchBackend:
    """A dense-embedding backend, parametrized by whichever `search_models`
    row of kind "dense_embedding" is passed to rank() — a future second
    embedding model needs no new backend class, only a new registry row
    (see migrations/versions/0005_search_models.py).

    There is no discrete "matched term" concept for a dense vector, so
    matched_terms is always empty for these hits (see SearchService).
    """

    def __init__(self, session: AsyncSession, nlp_client: NlpServiceClient) -> None:
        self._documents = DocumentRepository(session)
        self._embeddings = EmbeddingRepository(session)
        self._nlp = nlp_client

    async def rank(
        self, *, collection: Collection, text: str, model_row: SearchModel
    ) -> tuple[list[tuple[int, float]], dict[int, list[str]]]:
        query_vector = pad_to_max_dim(await self._nlp.embed_query(text))
        document_ids = await self._documents.list_ids_by_collection(collection.id)
        if not document_ids:
            return [], {}
        ranked = await self._embeddings.nearest(document_ids, model_row.id, query_vector)
        return ranked, {}
