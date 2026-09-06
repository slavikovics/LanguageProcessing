from __future__ import annotations

from ips_db import MetricResult
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession


class MetricResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_run(self, search_run_id: int, metrics: dict[str, float]) -> None:
        await self._session.execute(
            delete(MetricResult).where(MetricResult.search_run_id == search_run_id)
        )
        if metrics:
            rows = [
                {"search_run_id": search_run_id, "metric_name": name, "value": value}
                for name, value in metrics.items()
            ]
            await self._session.execute(insert(MetricResult), rows)

    async def list_for_run(self, search_run_id: int) -> list[MetricResult]:
        result = await self._session.execute(
            select(MetricResult).where(MetricResult.search_run_id == search_run_id)
        )
        return list(result.scalars().all())
