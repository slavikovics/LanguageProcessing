
from __future__ import annotations

from dataclasses import dataclass


class MetricsError(ValueError):
    pass


@dataclass(frozen=True)
class QueryMetrics:

    query_id: int
    query_text: str
    search_run_id: int
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


@dataclass(frozen=True)
class CollectionMetricsSummary:
    collection_id: int
    model: str
    model_label: str
    map: float
    mean_recall_at_5: float
    mean_recall_at_10: float
    mean_f1_at_5: float
    mean_f1_at_10: float
    mean_r_precision: float
    mean_precision_at_5: float
    mean_precision_at_10: float
    queries: list[QueryMetrics]
    curve: list[tuple[float, float]]
    unscored_judged_queries: int = 0


def mean_of(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def average_curves(curves: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    if not curves:
        return []
    levels = [level for level, _ in curves[0]]
    return [
        (level, sum(curve[i][1] for curve in curves) / len(curves))
        for i, level in enumerate(levels)
    ]
