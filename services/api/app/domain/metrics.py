"""Pure result shapes + the curve-averaging helper for the quality
evaluation feature (docs/PROJECT_PLAN.md, stage 5; formulas from
tasks/romip_metrics.pdf, the official ROMIP'2004 search-track metric set).
Score computation itself lives in nlp_core and is reached through
nlp-service, same as search — this module only holds logic with no business
making an HTTP call.
"""

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
    precision: float
    recall: float
    f1: float
    precision_at_5: float
    precision_at_10: float
    average_precision: float
    r_precision: float
    curve: list[tuple[float, float]]


@dataclass(frozen=True)
class CollectionMetricsSummary:
    collection_id: int
    map: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    queries: list[QueryMetrics]
    curve: list[tuple[float, float]]


def average_curves(curves: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    """Element-wise mean of several 11-point interpolated P/R curves that
    all share the same recall levels — one representative curve for a set
    of test queries, per romip_metrics.pdf section 1.3.4's Prec(r_i)
    formula (a plain arithmetic mean of each query's interpolated precision
    at that recall level)."""
    if not curves:
        return []
    levels = [level for level, _ in curves[0]]
    return [
        (level, sum(curve[i][1] for curve in curves) / len(curves))
        for i, level in enumerate(levels)
    ]
