"""IR quality metrics in the ROMIP/TREC style: Precision, Recall, F1,
Average Precision, MAP, R-Precision and the 11-point interpolated
precision/recall curve.

Each function takes a ranked list of document ids and the set of ids judged
relevant for that query (qrels) — no dependency on how the ranking or the
judgments were produced, so the same code evaluates lab 1's search and,
later, lab 2/3's own accuracy measurements.
"""

from __future__ import annotations

from typing import Hashable, Iterable, Sequence

DocId = Hashable


def precision_at_k(ranked_ids: Sequence[DocId], relevant_ids: set[DocId], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = ranked_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / len(top_k)


def recall_at_k(ranked_ids: Sequence[DocId], relevant_ids: set[DocId], k: int) -> float:
    if not relevant_ids:
        return 0.0
    top_k = ranked_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / len(relevant_ids)


def f1_score(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def average_precision(ranked_ids: Sequence[DocId], relevant_ids: set[DocId]) -> float:
    """AP: mean of precision@k evaluated at every rank k holding a relevant
    document, normalized by the total number of relevant documents."""
    if not relevant_ids:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for k, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in relevant_ids:
            hits += 1
            precision_sum += hits / k
    return precision_sum / len(relevant_ids)


def mean_average_precision(
    runs: Iterable[tuple[Sequence[DocId], set[DocId]]],
) -> float:
    """MAP: average of average_precision() over several query runs."""
    aps = [average_precision(ranked, relevant) for ranked, relevant in runs]
    if not aps:
        return 0.0
    return sum(aps) / len(aps)


def r_precision(ranked_ids: Sequence[DocId], relevant_ids: set[DocId]) -> float:
    """Precision computed at rank R = |relevant_ids| — comparable across
    queries with different numbers of relevant documents."""
    r = len(relevant_ids)
    if r == 0:
        return 0.0
    return precision_at_k(ranked_ids, relevant_ids, r)


def interpolated_precision_recall(
    ranked_ids: Sequence[DocId],
    relevant_ids: set[DocId],
    recall_levels: Sequence[float] = tuple(i / 10 for i in range(11)),
) -> list[tuple[float, float]]:
    """The classic 11-point interpolated precision/recall curve: for each
    fixed recall level r, the interpolated precision is the maximum
    precision observed anywhere in the ranking with actual recall >= r.
    """
    if not relevant_ids:
        return [(level, 0.0) for level in recall_levels]

    observed: list[tuple[float, float]] = []
    hits = 0
    for k, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in relevant_ids:
            hits += 1
        observed.append((hits / len(relevant_ids), hits / k))

    curve: list[tuple[float, float]] = []
    for level in recall_levels:
        candidates = [precision for recall, precision in observed if recall >= level]
        curve.append((level, max(candidates) if candidates else 0.0))
    return curve
