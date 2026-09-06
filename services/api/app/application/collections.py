from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.collections import CollectionRepository
from app.infrastructure.repositories.crawl_jobs import CrawlJobRepository
from app.infrastructure.repositories.index_jobs import IndexJobRepository

_ACTIVE_INDEX_STATUSES = {"pending", "running"}
_ACTIVE_CRAWL_STATUSES = {"pending", "running"}


class CollectionNotFound(Exception):
    pass


class CollectionBusy(Exception):
    """Raised when deleting a collection would pull the rug out from under
    a background job still writing rows for its documents (an in-flight
    index job reading document_terms, or a crawl job about to insert new
    documents/touch the collection)."""


class CollectionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._collections = CollectionRepository(session)
        self._index_jobs = IndexJobRepository(session)
        self._crawl_jobs = CrawlJobRepository(session)

    async def delete(self, collection_id: int) -> None:
        collection = await self._collections.get(collection_id)
        if collection is None:
            raise CollectionNotFound(f"collection {collection_id} not found")

        latest_index_job = await self._index_jobs.latest_for_collection(collection_id)
        if latest_index_job is not None and latest_index_job.status in _ACTIVE_INDEX_STATUSES:
            raise CollectionBusy(
                "collection is being indexed; wait for indexing to finish before deleting it"
            )

        jobs = await self._crawl_jobs.list(collection_id=collection_id, limit=1000)
        if any(job.status in _ACTIVE_CRAWL_STATUSES for job in jobs):
            raise CollectionBusy(
                "collection has an active crawl job; wait for it to finish before deleting it"
            )

        await self._collections.delete(collection)
        await self._session.commit()
