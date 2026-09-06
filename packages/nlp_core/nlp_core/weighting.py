"""TF-IDF term-weighting primitives, operating on plain dicts keyed by an
arbitrary hashable term id (a lemma string, or a numeric id once persisted).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Hashable, Iterable, Mapping

Term = Hashable


def term_frequencies(terms: Iterable[Term]) -> dict[Term, int]:
    """Q_i — raw term counts within a single document (or query)."""
    return dict(Counter(terms))


def document_frequencies(documents_terms: Iterable[Iterable[Term]]) -> dict[Term, int]:
    """Number of *documents* (not raw occurrences) each term appears in."""
    counts: dict[Term, int] = {}
    for doc_terms in documents_terms:
        for term in set(doc_terms):
            counts[term] = counts.get(term, 0) + 1
    return counts


def inverse_document_frequency(
    document_frequency: Mapping[Term, int], total_documents: int
) -> dict[Term, float]:
    """idf = log(N / document_frequency)."""
    if total_documents <= 0:
        raise ValueError("total_documents must be positive")
    return {
        term: math.log(total_documents / doc_count)
        for term, doc_count in document_frequency.items()
        if doc_count > 0
    }


def term_weights(term_freqs: Mapping[Term, int], idf: Mapping[Term, float]) -> dict[Term, float]:
    """Un-normalized tf-idf weight of each term in a document."""
    return {term: freq * idf.get(term, 0.0) for term, freq in term_freqs.items()}


def normalized_tfidf_vector(
    term_freqs: Mapping[Term, int], idf: Mapping[Term, float]
) -> dict[Term, float]:
    """L2-normalized TF-IDF vector, so cosine similarity against a
    same-normalized query vector reduces to a plain dot product."""
    raw = term_weights(term_freqs, idf)
    norm = math.sqrt(sum(weight * weight for weight in raw.values()))
    if norm == 0:
        return {term: 0.0 for term in raw}
    return {term: weight / norm for term, weight in raw.items()}


def binary_query_vector(query_terms: Iterable[Term]) -> dict[Term, float]:
    """Binary query vector: 1.0 for each present term, implicit 0 otherwise."""
    return {term: 1.0 for term in set(query_terms)}
