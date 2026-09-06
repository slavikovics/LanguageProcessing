from __future__ import annotations

from ips_db import DocumentChunk
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession


class ChunkRepository:
    """Writes/reads document_chunks — a document split into pieces so a
    dense embedding model encodes each within its own context window
    instead of silently truncating anything past the token limit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def clear_for_documents(self, document_ids: list[int]) -> None:
        if not document_ids:
            return
        await self._session.execute(delete(DocumentChunk).where(DocumentChunk.document_id.in_(document_ids)))

    async def bulk_create(self, rows: list[dict[str, object]]) -> list[DocumentChunk]:
        """rows: [{document_id, chunk_index, text}, ...]. Returns persisted
        rows (ids assigned) in the same order, to zip against encoded vectors."""
        if not rows:
            return []
        chunks = [DocumentChunk(**row) for row in rows]
        self._session.add_all(chunks)
        await self._session.flush()
        return chunks
