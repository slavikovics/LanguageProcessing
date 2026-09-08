from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.metrics import (
    CollectionMetricsSummary,
    MetricsError,
    QueryMetrics,
    average_curves,
    mean_of,
)
from app.domain.search import DEFAULT_TOP_K, SearchError
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories.judgments import RelevanceJudgmentRepository
from app.infrastructure.repositories.metrics import MetricResultRepository
from app.infrastructure.repositories.queries import QueryRepository
from app.infrastructure.repositories.search_models import SearchModelRepository


class MetricsService:

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
                "precision_at_5": evaluated["precision_at_5"],
                "precision_at_10": evaluated["precision_at_10"],
                "recall_at_5": evaluated["recall_at_5"],
                "recall_at_10": evaluated["recall_at_10"],
                "f1_at_5": evaluated["f1_at_5"],
                "f1_at_10": evaluated["f1_at_10"],
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
            precision_at_5=evaluated["precision_at_5"],
            precision_at_10=evaluated["precision_at_10"],
            recall_at_5=evaluated["recall_at_5"],
            recall_at_10=evaluated["recall_at_10"],
            f1_at_5=evaluated["f1_at_5"],
            f1_at_10=evaluated["f1_at_10"],
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
                unscored_judged_queries += 1
                continue
            run = await self._queries.latest_search_run_for_query(query.id, model_id=model_row.id)
            if run is None:
                continue

            query_metrics = await self.evaluate_run(run.id)
            per_query.append(query_metrics)

        if not per_query:
            return CollectionMetricsSummary(
                collection_id=collection_id,
                model=model_row.key,
                model_label=model_row.label,
                map=0.0,
                mean_recall_at_5=0.0,
                mean_recall_at_10=0.0,
                mean_f1_at_5=0.0,
                mean_f1_at_10=0.0,
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
            map=mean_of([q.average_precision for q in per_query]),
            mean_recall_at_5=mean_of([q.recall_at_5 for q in per_query]),
            mean_recall_at_10=mean_of([q.recall_at_10 for q in per_query]),
            mean_f1_at_5=mean_of([q.f1_at_5 for q in per_query]),
            mean_f1_at_10=mean_of([q.f1_at_10 for q in per_query]),
            mean_r_precision=mean_of([q.r_precision for q in per_query]),
            mean_precision_at_5=mean_of([q.precision_at_5 for q in per_query]),
            mean_precision_at_10=mean_of([q.precision_at_10 for q in per_query]),
            queries=per_query,
            curve=curve,
            unscored_judged_queries=unscored_judged_queries,
        )

    async def compare(self, collection_id: int, models: list[str]) -> list[CollectionMetricsSummary]:
        return [await self.collection_summary(collection_id, model=key) for key in models]

    async def rerun_all_and_compare(
        self, collection_id: int, models: list[str]
    ) -> list[CollectionMetricsSummary]:
        from app.application.search import SearchService

        queries = await self._queries.list_queries_by_collection(collection_id)
        search_service = SearchService(self._session, self._nlp)
        for query in queries:
            if not await self._judgments.list_for_query(query.id):
                continue
            for model_key in models:
                try:
                    await search_service.search(
                        collection_id=collection_id, text=query.text, top_k=DEFAULT_TOP_K, model=model_key
                    )
                except SearchError:
                    continue

        return await self.compare(collection_id, models)
