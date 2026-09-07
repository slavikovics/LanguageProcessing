from __future__ import annotations

from ips_db import Document

from app.domain.lang_id import LangIdError
from app.infrastructure.repositories.chunk_embeddings import ChunkEmbeddingRepository
from app.infrastructure.repositories.search_models import SearchModelRepository


async def stored_vectors_for(
    documents: list[Document],
    *,
    chunk_embeddings: ChunkEmbeddingRepository,
    search_models: SearchModelRepository,
) -> list[list[float]]:
    """Reuses each document's chunk_index=0 embedding, computed once during
    search indexing, instead of re-requesting it from OpenRouter — indexing
    the collection is a prerequisite for both neural training and neural
    testing precisely so this lookup can be instant."""
    active_models = await search_models.list_active()
    dense_model = next((m for m in active_models if m.kind == "dense_embedding"), None)
    if dense_model is None:
        raise LangIdError("no active dense-embedding search model — index a collection first")

    document_ids = [document.id for document in documents]
    vectors_by_id = await chunk_embeddings.get_first_chunk_vectors(document_ids, dense_model.id)
    missing = [document.id for document in documents if document.id not in vectors_by_id]
    if missing:
        raise LangIdError(
            f"{len(missing)} document(s) have no stored embedding yet — index their "
            "collection(s) before training or testing the neural classifier"
        )
    return [vectors_by_id[document.id] for document in documents]
