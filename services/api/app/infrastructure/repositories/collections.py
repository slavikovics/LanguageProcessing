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
        collection = await self._session.get(Collection, collection_id)
        if collection is not None:
            collection.documents_changed_at = dt.datetime.utcnow()
            await self._session.flush()
