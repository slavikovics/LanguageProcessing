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
    """precision(n) per ROMIP'2004 section 1.3.1: relevant docs among the
    first k, divided by k itself — *not* by the number actually retrieved.
    A system that returns fewer than k documents is scored as if the
    missing slots were non-relevant, so precision@k only ever drops as k
    grows past what the system returned (matches the methodology's note
    that a short result list can't score above the system's own overall
    precision)."""
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


def micro_average_precision_recall(
    runs: Iterable[tuple[Sequence[DocId], set[DocId]]],
) -> tuple[float, float]:
    """Micro-averaged precision/recall over several query runs — the
    ROMIP'2004 methodology (section 1.2) specifies micro-averaging (not
    macro/mean-of-per-query) for precision/recall on the search track: sum
    the contingency-table counts (a = relevant∩retrieved, over all queries)
    first, then divide, rather than averaging each query's own ratio.
    """
    total_hits = 0
    total_retrieved = 0
    total_relevant = 0
    for ranked_ids, relevant_ids in runs:
        hits = sum(1 for doc_id in ranked_ids if doc_id in relevant_ids)
        total_hits += hits
        total_retrieved += len(ranked_ids)
        total_relevant += len(relevant_ids)

    precision = total_hits / total_retrieved if total_retrieved else 0.0
    recall = total_hits / total_relevant if total_relevant else 0.0
    return precision, recall


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
