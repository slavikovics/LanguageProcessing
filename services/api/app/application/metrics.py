from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.metrics import CollectionMetricsSummary, MetricsError, QueryMetrics, average_curves
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories import (
    MetricResultRepository,
    QueryRepository,
    RelevanceJudgmentRepository,
)


class MetricsService:
    """Оценка качества (docs/PROJECT_PLAN.md, stage 5; formulas from the
    official ROMIP'2004 methodology, tasks/romip_metrics.pdf): scores one
    search run against its query's relevance judgments (qrels), or rolls up
    every judged query in a collection into MAP + micro-averaged P/R/F1 + an
    averaged 11-point curve for the report.
    """

    def __init__(self, session: AsyncSession, nlp_client: NlpServiceClient | None = None) -> None:
        self._session = session
        self._queries = QueryRepository(session)
        self._judgments = RelevanceJudgmentRepository(session)
        self._metric_results = MetricResultRepository(session)
        self._nlp = nlp_client or NlpServiceClient()

    async def evaluate_run(self, search_run_id: int) -> QueryMetrics:
        run = await self._queries.get_search_run(search_run_id)
        if run is None:
            raise MetricsError(f"search run {search_run_id} not found")

        results = await self._queries.list_results(search_run_id)
        ranked_ids = [row.document_id for row in results]
        relevant_ids = await self._judgments.relevant_document_ids(run.query_id)

        evaluated = await self._nlp.evaluate_metrics(ranked_ids, list(relevant_ids))

        await self._metric_results.replace_for_run(
            search_run_id,
            {
                "precision": evaluated["precision"],
                "recall": evaluated["recall"],
                "f1": evaluated["f1"],
                "precision_at_5": evaluated["precision_at_5"],
                "precision_at_10": evaluated["precision_at_10"],
                "average_precision": evaluated["average_precision"],
                "r_precision": evaluated["r_precision"],
            },
        )
        await self._session.commit()

        query = await self._queries.get_query(run.query_id)
        return QueryMetrics(
            query_id=run.query_id,
            query_text=query.text if query is not None else "",
            search_run_id=search_run_id,
            retrieved_count=evaluated["retrieved_count"],
            relevant_count=evaluated["relevant_count"],
            precision=evaluated["precision"],
            recall=evaluated["recall"],
            f1=evaluated["f1"],
            precision_at_5=evaluated["precision_at_5"],
            precision_at_10=evaluated["precision_at_10"],
            average_precision=evaluated["average_precision"],
            r_precision=evaluated["r_precision"],
            curve=[tuple(point) for point in evaluated["curve"]],
        )

    async def collection_summary(self, collection_id: int) -> CollectionMetricsSummary:
        queries = await self._queries.list_queries_by_collection(collection_id)

        per_query: list[QueryMetrics] = []
        runs_for_aggregate: list[tuple[list[int], list[int]]] = []
        for query in queries:
            judgments = await self._judgments.list_for_query(query.id)
            if not judgments:
                continue
            relevant_ids = await self._judgments.relevant_document_ids(query.id)
            if not relevant_ids:
                # romip_metrics.pdf, section 1: queries with no relevant
                # documents are excluded from metric computation (0/0).
                continue
            run = await self._queries.latest_search_run_for_query(query.id)
            if run is None:
                continue

            query_metrics = await self.evaluate_run(run.id)
            per_query.append(query_metrics)

            results = await self._queries.list_results(run.id)
            runs_for_aggregate.append(([row.document_id for row in results], list(relevant_ids)))

        if not per_query:
            return CollectionMetricsSummary(
                collection_id=collection_id,
                map=0.0,
                micro_precision=0.0,
                micro_recall=0.0,
                micro_f1=0.0,
                queries=[],
                curve=[],
            )

        aggregate = await self._nlp.aggregate_metrics(runs_for_aggregate)
        curve = average_curves([q.curve for q in per_query])

        return CollectionMetricsSummary(
            collection_id=collection_id,
            map=aggregate["map"],
            micro_precision=aggregate["micro_precision"],
            micro_recall=aggregate["micro_recall"],
            micro_f1=aggregate["micro_f1"],
            queries=per_query,
            curve=curve,
        )
