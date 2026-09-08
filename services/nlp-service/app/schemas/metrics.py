from pydantic import BaseModel


class MetricsEvaluateRequest(BaseModel):
    ranked_ids: list[int]
    relevant_ids: list[int]


class MetricsEvaluateResponse(BaseModel):

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
