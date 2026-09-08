from __future__ import annotations

from ips_db import Document, DocumentTerm, TermWeight
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession


class IndexRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def clear_for_documents(self, document_ids: list[int]) -> None:
        if not document_ids:
            return
        await self._session.execute(
            delete(DocumentTerm).where(DocumentTerm.document_id.in_(document_ids))
        )
        await self._session.execute(
            delete(TermWeight).where(TermWeight.document_id.in_(document_ids))
        )

    async def bulk_write(
        self, document_terms: list[dict[str, int]], term_weights: list[dict[str, object]]
    ) -> None:
        if document_terms:
            await self._session.execute(insert(DocumentTerm), document_terms)
        if term_weights:
            await self._session.execute(insert(TermWeight), term_weights)

    async def load_document_vectors(
        self, document_ids: list[int], term_ids: list[int]
    ) -> dict[int, dict[int, float]]:
        if not document_ids or not term_ids:
            return {}
        result = await self._session.execute(
            select(TermWeight.document_id, TermWeight.term_id, TermWeight.weight).where(
                TermWeight.document_id.in_(document_ids), TermWeight.term_id.in_(term_ids)
            )
        )
        vectors: dict[int, dict[int, float]] = {}
        for document_id, term_id, weight in result.all():
            vectors.setdefault(document_id, {})[term_id] = weight
        return vectors

    async def document_frequency(self, collection_id: int, term_ids: list[int]) -> dict[int, int]:
        if not term_ids:
            return {}
        result = await self._session.execute(
            select(DocumentTerm.term_id, func.count(func.distinct(DocumentTerm.document_id)))
            .join(Document, Document.id == DocumentTerm.document_id)
            .where(Document.collection_id == collection_id, DocumentTerm.term_id.in_(term_ids))
            .group_by(DocumentTerm.term_id)
        )
        return {term_id: count for term_id, count in result.all()}

    async def indexed_term_count(self, document_ids: list[int]) -> int:
        if not document_ids:
            return 0
        result = await self._session.execute(
            select(func.count(func.distinct(TermWeight.term_id))).where(
                TermWeight.document_id.in_(document_ids)
            )
        )
        return int(result.scalar_one())
