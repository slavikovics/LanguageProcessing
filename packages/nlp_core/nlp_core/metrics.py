
from __future__ import annotations

from typing import Hashable, Sequence

DocId = Hashable


def precision_at_k(ranked_ids: Sequence[DocId], relevant_ids: set[DocId], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = ranked_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / k


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
    if not relevant_ids:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for k, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in relevant_ids:
            hits += 1
            precision_sum += hits / k
    return precision_sum / len(relevant_ids)


def r_precision(ranked_ids: Sequence[DocId], relevant_ids: set[DocId]) -> float:
    r = len(relevant_ids)
    if r == 0:
        return 0.0
    return precision_at_k(ranked_ids, relevant_ids, r)


def interpolated_precision_recall(
    ranked_ids: Sequence[DocId],
    relevant_ids: set[DocId],
    recall_levels: Sequence[float] = tuple(i / 10 for i in range(11)),
) -> list[tuple[float, float]]:
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
