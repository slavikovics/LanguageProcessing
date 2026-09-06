from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.metrics import (
    CollectionMetricsSummary,
    MetricsError,
    QueryMetrics,
    average_curves,
    mean_of,
)
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories import (
    MetricResultRepository,
    QueryRepository,
    RelevanceJudgmentRepository,
    SearchModelRepository,
)


class MetricsService:
    """Оценка качества (docs/PROJECT_PLAN.md, stage 5; formulas from the
    official ROMIP'2004 methodology, tasks/romip_metrics.pdf): scores one
    search run against its query's relevance judgments (qrels), or rolls up
    every judged query in a collection into MAP + mean R-precision/P@5/P@10
    + an averaged 11-point curve for the report — scoped to one search model
    at a time, so multiple models' summaries can be compared side by side
    (see compare()).
    """

    def __init__(self, session: AsyncSession, nlp_client: NlpServiceClient | None = None) -> None:
        self._session = session
        self._queries = QueryRepository(session)
        self._judgments = RelevanceJudgmentRepository(session)
        self._metric_results = MetricResultRepository(session)
        self._models = SearchModelRepository(session)
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

    async def collection_summary(
        self, collection_id: int, *, model: str = "tfidf"
    ) -> CollectionMetricsSummary:
        model_row = await self._models.get_by_key(model)
        if model_row is None:
            raise MetricsError(f"unknown search model '{model}'")

        queries = await self._queries.list_queries_by_collection(collection_id)

        per_query: list[QueryMetrics] = []
        unscored_judged_queries = 0
        for query in queries:
            judgments = await self._judgments.list_for_query(query.id)
            if not judgments:
                continue
            relevant_ids = await self._judgments.relevant_document_ids(query.id)
            if not relevant_ids:
                # romip_metrics.pdf, section 1: queries with no relevant
                # documents are excluded from metric computation (0/0).
                unscored_judged_queries += 1
                continue
            run = await self._queries.latest_search_run_for_query(query.id, model_id=model_row.id)
            if run is None:
                # This model hasn't been used to search this query yet —
                # it simply doesn't contribute a row for it, rather than
                # showing a misleading zero.
                continue

            query_metrics = await self.evaluate_run(run.id)
            per_query.append(query_metrics)

        if not per_query:
            return CollectionMetricsSummary(
                collection_id=collection_id,
                model=model_row.key,
                model_label=model_row.label,
                map=0.0,
                mean_r_precision=0.0,
                mean_precision_at_5=0.0,
                mean_precision_at_10=0.0,
                queries=[],
                curve=[],
                unscored_judged_queries=unscored_judged_queries,
            )

        curve = average_curves([q.curve for q in per_query])

        return CollectionMetricsSummary(
            collection_id=collection_id,
            model=model_row.key,
            model_label=model_row.label,
            # MAP is defined as the mean of each query's own AP
            # (romip_metrics.pdf section 1.3.3), same macro-average as
            # R-precision/precision(n) below — no separate aggregation call
            # needed.
            map=mean_of([q.average_precision for q in per_query]),
            mean_r_precision=mean_of([q.r_precision for q in per_query]),
            mean_precision_at_5=mean_of([q.precision_at_5 for q in per_query]),
            mean_precision_at_10=mean_of([q.precision_at_10 for q in per_query]),
            queries=per_query,
            curve=curve,
            unscored_judged_queries=unscored_judged_queries,
        )

    async def compare(self, collection_id: int, models: list[str]) -> list[CollectionMetricsSummary]:
        """One collection_summary() per requested model key — collection
        sizes here are course-project scale, so a sequential loop needs no
        concurrency machinery."""
        return [await self.collection_summary(collection_id, model=key) for key in models]
