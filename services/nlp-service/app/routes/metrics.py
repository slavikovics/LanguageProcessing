from fastapi import APIRouter
from nlp_core import metrics

from app.schemas.metrics import MetricsEvaluateRequest, MetricsEvaluateResponse

router = APIRouter(tags=["nlp"])


@router.post("/metrics/evaluate", response_model=MetricsEvaluateResponse)
async def evaluate_metrics(payload: MetricsEvaluateRequest) -> MetricsEvaluateResponse:
    """Computes rank-quality metrics for one ranked list against its qrels."""
    relevant = set(payload.relevant_ids)
    n = len(payload.ranked_ids)
    precision_at_5 = metrics.precision_at_k(payload.ranked_ids, relevant, 5)
    precision_at_10 = metrics.precision_at_k(payload.ranked_ids, relevant, 10)
    recall_at_5 = metrics.recall_at_k(payload.ranked_ids, relevant, 5)
    recall_at_10 = metrics.recall_at_k(payload.ranked_ids, relevant, 10)
    return MetricsEvaluateResponse(
        retrieved_count=n,
        relevant_count=len(relevant),
        precision_at_5=precision_at_5,
        precision_at_10=precision_at_10,
        recall_at_5=recall_at_5,
        recall_at_10=recall_at_10,
        f1_at_5=metrics.f1_score(precision_at_5, recall_at_5),
        f1_at_10=metrics.f1_score(precision_at_10, recall_at_10),
        average_precision=metrics.average_precision(payload.ranked_ids, relevant),
        r_precision=metrics.r_precision(payload.ranked_ids, relevant),
        curve=metrics.interpolated_precision_recall(payload.ranked_ids, relevant),
    )
