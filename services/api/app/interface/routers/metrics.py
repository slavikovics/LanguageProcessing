from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.metrics import MetricsService
from app.core.database import get_db
from app.domain.metrics import MetricsError
from app.infrastructure.repositories import (
    QueryRepository,
    RelevanceJudgmentRepository,
    SearchModelRepository,
)
from app.interface.schemas import (
    CollectionMetricsSummaryOut,
    MetricsCompareResponseOut,
    QueryMetricsOut,
    QueryOut,
    RelevanceJudgmentIn,
    RelevanceJudgmentOut,
)

router = APIRouter(tags=["metrics"])


@router.get("/collections/{collection_id}/queries", response_model=list[QueryOut])
async def list_collection_queries(
    collection_id: int, db: AsyncSession = Depends(get_db)
) -> list[QueryOut]:
    repo = QueryRepository(db)
    return await repo.list_queries_by_collection(collection_id)


@router.put("/queries/{query_id}/judgments/{document_id}", response_model=RelevanceJudgmentOut)
async def set_judgment(
    query_id: int,
    document_id: int,
    payload: RelevanceJudgmentIn,
    db: AsyncSession = Depends(get_db),
) -> RelevanceJudgmentOut:
    repo = RelevanceJudgmentRepository(db)
    await repo.set_judgment(query_id=query_id, document_id=document_id, is_relevant=payload.is_relevant)
    await db.commit()
    return RelevanceJudgmentOut(document_id=document_id, is_relevant=payload.is_relevant)


@router.delete("/queries/{query_id}/judgments/{document_id}", status_code=204)
async def clear_judgment(query_id: int, document_id: int, db: AsyncSession = Depends(get_db)) -> None:
    repo = RelevanceJudgmentRepository(db)
    await repo.clear_judgment(query_id=query_id, document_id=document_id)
    await db.commit()


@router.get("/queries/{query_id}/judgments", response_model=list[RelevanceJudgmentOut])
async def list_judgments(query_id: int, db: AsyncSession = Depends(get_db)) -> list[RelevanceJudgmentOut]:
    repo = RelevanceJudgmentRepository(db)
    judgments = await repo.list_for_query(query_id)
    return [
        RelevanceJudgmentOut(document_id=j.document_id, is_relevant=j.is_relevant) for j in judgments
    ]


@router.post("/search-runs/{search_run_id}/metrics", response_model=QueryMetricsOut)
async def evaluate_search_run(
    search_run_id: int, db: AsyncSession = Depends(get_db)
) -> QueryMetricsOut:
    service = MetricsService(db)
    try:
        return await service.evaluate_run(search_run_id)
    except MetricsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/collections/{collection_id}/metrics/summary", response_model=CollectionMetricsSummaryOut)
async def collection_metrics_summary(
    collection_id: int, model: str = "tfidf", db: AsyncSession = Depends(get_db)
) -> CollectionMetricsSummaryOut:
    service = MetricsService(db)
    try:
        return await service.collection_summary(collection_id, model=model)
    except MetricsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/collections/{collection_id}/metrics/compare", response_model=MetricsCompareResponseOut)
async def collection_metrics_compare(
    collection_id: int, models: str = "", db: AsyncSession = Depends(get_db)
) -> MetricsCompareResponseOut:
    """`models` is a comma-separated list of search model keys; empty means
    every currently active model (see GET /search-models)."""
    model_keys = [key for key in models.split(",") if key]
    if not model_keys:
        model_keys = [row.key for row in await SearchModelRepository(db).list_active()]

    service = MetricsService(db)
    try:
        summaries = await service.compare(collection_id, model_keys)
    except MetricsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MetricsCompareResponseOut(summaries=summaries)
