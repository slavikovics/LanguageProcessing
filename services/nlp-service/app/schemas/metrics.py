from pydantic import BaseModel


class MetricsEvaluateRequest(BaseModel):
    ranked_ids: list[int]
    relevant_ids: list[int]


class MetricsEvaluateResponse(BaseModel):
    """Rank-quality metrics for one query. Whole-list Precision/Recall/F1 are
    omitted — this system always ranks the full collection, so they'd
    degenerate (Recall≡1, Precision≈relevant/collection_size). The @5/@10
    cutoff variants below stay meaningful instead."""

    retrieved_count: int
    relevant_count: int
    precision_at_5: float
    precision_at_10: float
    recall_at_5: float
    recall_at_10: float
    f1_at_5: float
    f1_at_10: float
    average_precision: float
    r_precision: float
    curve: list[tuple[float, float]]
