"""Result shapes and the curve-averaging helper for the quality-evaluation
feature. Score computation itself lives in nlp_core, reached through
nlp-service, same as search.
"""

from __future__ import annotations

from dataclasses import dataclass


class MetricsError(ValueError):
    pass


@dataclass(frozen=True)
class QueryMetrics:
    """Whole-list Precision/Recall/F1 are omitted — this system always ranks
    the full collection, so they'd degenerate (Recall≡1). The @5/@10 cutoff
    variants below stay meaningful instead."""

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
    # Judged queries excluded above because none of their judgments is
    # "relevant" — recall/AP are undefined, not zero, at zero relevant docs.
    unscored_judged_queries: int = 0


def mean_of(values: list[float]) -> float:
    """Macro-average across queries — mean of each query's own value, the
    standard TREC convention (parallel to "MAP = mean of AP")."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def average_curves(curves: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    """Element-wise mean of several 11-point P/R curves sharing the same
    recall levels — one representative curve for a set of test queries."""
    if not curves:
        return []
    levels = [level for level, _ in curves[0]]
    return [
        (level, sum(curve[i][1] for curve in curves) / len(curves))
        for i, level in enumerate(levels)
    ]
