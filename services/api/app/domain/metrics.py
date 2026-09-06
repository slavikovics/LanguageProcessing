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
    model: str
    model_label: str
    map: float
    mean_r_precision: float
    mean_precision_at_5: float
    mean_precision_at_10: float
    queries: list[QueryMetrics]
    curve: list[tuple[float, float]]
    unscored_judged_queries: int = 0
    """Queries that have relevance judgments but were left out of the
    numbers above because none of those judgments is "relevant" — recall
    and AP are undefined at zero relevant documents (romip_metrics.pdf,
    section 1), not merely zero. Surfaced separately so the UI can tell
    this apart from "nothing has been judged yet"."""


def mean_of(values: list[float]) -> float:
    """Macro-average across queries — the same aggregation MAP itself uses
    for average_precision (romip_metrics.pdf doesn't spell out how to roll
    up R-precision/precision(n) across queries, but this is the standard
    TREC convention: report the mean of each query's own value, exactly
    parallel to "MAP = mean of AP")."""
    if not values:
        return 0.0
    return sum(values) / len(values)


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
