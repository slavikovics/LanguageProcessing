from __future__ import annotations

from ips_db import Query, SearchResult, SearchRun
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession


class QueryRepository:
    """Persists Query/SearchRun/SearchResult — the audit trail relevance
    judgments and metric results build on."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_query(self, *, collection_id: int, text: str) -> Query:
        """Reuses the existing Query row for this (collection, text) pair:
        judgments are keyed by query_id, so re-running the same query text
        must land on the same query for judgments to accumulate into one
        qrel set — otherwise recall would be trivially 1.0 against a set
        that never extends past a single run's own results."""
        result = await self._session.execute(
            select(Query).where(Query.collection_id == collection_id, Query.text == text)
        )
        existing = result.scalars().first()
        if existing is not None:
            return existing
        query = Query(collection_id=collection_id, text=text)
        self._session.add(query)
        await self._session.flush()
        return query

    async def get_query(self, query_id: int) -> Query | None:
        return await self._session.get(Query, query_id)

    async def list_queries_by_collection(self, collection_id: int) -> list[Query]:
        result = await self._session.execute(
            select(Query).where(Query.collection_id == collection_id).order_by(Query.id.desc())
        )
        return list(result.scalars().all())

    async def create_search_run(self, *, query_id: int, model_id: int) -> SearchRun:
        run = SearchRun(query_id=query_id, model_id=model_id)
        self._session.add(run)
        await self._session.flush()
        return run

    async def get_search_run(self, search_run_id: int) -> SearchRun | None:
        return await self._session.get(SearchRun, search_run_id)

    async def latest_search_run_for_query(self, query_id: int, *, model_id: int) -> SearchRun | None:
        result = await self._session.execute(
            select(SearchRun)
            .where(SearchRun.query_id == query_id, SearchRun.model_id == model_id)
            .order_by(SearchRun.id.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def bulk_insert_results(
        self, search_run_id: int, hits: list[tuple[int, int, float]]
    ) -> None:
        """hits: list of (document_id, rank, score)."""
        if not hits:
            return
        rows = [
            {"search_run_id": search_run_id, "document_id": doc_id, "rank": rank, "score": score}
            for doc_id, rank, score in hits
        ]
        await self._session.execute(insert(SearchResult), rows)

    async def list_results(self, search_run_id: int) -> list[SearchResult]:
        result = await self._session.execute(
            select(SearchResult)
            .where(SearchResult.search_run_id == search_run_id)
            .order_by(SearchResult.rank)
        )
        return list(result.scalars().all())
