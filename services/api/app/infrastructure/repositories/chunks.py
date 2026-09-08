from __future__ import annotations

from ips_db import DocumentChunk
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession


class ChunkRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def clear_for_documents(self, document_ids: list[int]) -> None:
        if not document_ids:
            return
        await self._session.execute(delete(DocumentChunk).where(DocumentChunk.document_id.in_(document_ids)))

    async def bulk_create(self, rows: list[dict[str, object]]) -> list[DocumentChunk]:
        if not rows:
            return []
        chunks = [DocumentChunk(**row) for row in rows]
        self._session.add_all(chunks)
        await self._session.flush()
        return chunks
