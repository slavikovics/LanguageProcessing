from __future__ import annotations

import datetime as dt

from ips_db import Collection, Document
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class CollectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str, language: str) -> Collection:
        collection = Collection(name=name, language=language)
        self._session.add(collection)
        await self._session.flush()
        return collection

    async def get(self, collection_id: int) -> Collection | None:
        return await self._session.get(Collection, collection_id)

    async def delete(self, collection: Collection) -> None:
        """Relies on ON DELETE CASCADE to clear everything the collection owns."""
        await self._session.delete(collection)

    async def list(self) -> list[Collection]:
        result = await self._session.execute(select(Collection).order_by(Collection.id))
        return list(result.scalars().all())

    async def list_with_document_counts(self) -> list[tuple[Collection, int]]:
        result = await self._session.execute(
            select(Collection, func.count(Document.id))
            .outerjoin(Document, Document.collection_id == Collection.id)
            .group_by(Collection.id)
            .order_by(Collection.id)
        )
        return [(collection, count) for collection, count in result.all()]

    async def touch_documents_changed(self, collection_id: int) -> None:
        """Marks the collection's document set as changed now, so the UI can
        flag a stale index against the latest IndexJob's finished_at.

        Uses fetch-then-mutate rather than a bare Core UPDATE so an already
        -loaded Collection in this session's identity map picks up the new
        value immediately instead of staying stale.
        """
        collection = await self._session.get(Collection, collection_id)
        if collection is not None:
            collection.documents_changed_at = dt.datetime.utcnow()
            await self._session.flush()
