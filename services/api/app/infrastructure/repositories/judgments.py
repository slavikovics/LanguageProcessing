from __future__ import annotations

from ips_db import RelevanceJudgment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class RelevanceJudgmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set_judgment(self, *, query_id: int, document_id: int, is_relevant: bool) -> None:
        existing = await self._session.get(RelevanceJudgment, (query_id, document_id))
        if existing is not None:
            existing.is_relevant = is_relevant
        else:
            self._session.add(
                RelevanceJudgment(query_id=query_id, document_id=document_id, is_relevant=is_relevant)
            )
        await self._session.flush()

    async def clear_judgment(self, *, query_id: int, document_id: int) -> None:
        existing = await self._session.get(RelevanceJudgment, (query_id, document_id))
        if existing is not None:
            await self._session.delete(existing)
            await self._session.flush()

    async def relevant_document_ids(self, query_id: int) -> set[int]:
        result = await self._session.execute(
            select(RelevanceJudgment.document_id).where(
                RelevanceJudgment.query_id == query_id, RelevanceJudgment.is_relevant.is_(True)
            )
        )
        return {row[0] for row in result.all()}

    async def list_for_query(self, query_id: int) -> list[RelevanceJudgment]:
        result = await self._session.execute(
            select(RelevanceJudgment).where(RelevanceJudgment.query_id == query_id)
        )
        return list(result.scalars().all())
