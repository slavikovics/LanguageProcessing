"""Term-weighting primitives — formulas (1.5)/(1.6) and the normalized
TF-IDF vector from the "векторная модель поиска" section of the methodology.

Operates on plain ``dict``s keyed by an arbitrary hashable term identifier
(a lemma string, or a numeric term id once persisted) so the same code path
works both in unit tests and once wired to the database.
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
    """P_i for every term across a collection: the number of *documents*
    (not raw occurrences) each term appears in. Feed the result into
    :func:`inverse_document_frequency` together with N = number of documents.
    """
    counts: dict[Term, int] = {}
    for doc_terms in documents_terms:
        for term in set(doc_terms):
            counts[term] = counts.get(term, 0) + 1
    return counts


def inverse_document_frequency(
    document_frequency: Mapping[Term, int], total_documents: int
) -> dict[Term, float]:
    """B_i = log(N / P_i) — formula (1.5)."""
    if total_documents <= 0:
        raise ValueError("total_documents must be positive")
    return {
        term: math.log(total_documents / doc_count)
        for term, doc_count in document_frequency.items()
        if doc_count > 0
    }


def term_weights(term_freqs: Mapping[Term, int], idf: Mapping[Term, float]) -> dict[Term, float]:
    """A_i^j = Q_i^j * B_i — formula (1.6), the un-normalized weight of each
    term in a document."""
    return {term: freq * idf.get(term, 0.0) for term, freq in term_freqs.items()}


def normalized_tfidf_vector(
    term_freqs: Mapping[Term, int], idf: Mapping[Term, float]
) -> dict[Term, float]:
    """L2-normalized TF-IDF vector (the w_dk formula from the vector search
    model section): the (1.6) weights divided by the document's Euclidean
    norm, so cosine similarity against a query vector reduces to a plain dot
    product when the query is normalized the same way.
    """
    raw = term_weights(term_freqs, idf)
    norm = math.sqrt(sum(weight * weight for weight in raw.values()))
    if norm == 0:
        return {term: 0.0 for term in raw}
    return {term: weight / norm for term, weight in raw.items()}


def binary_query_vector(query_terms: Iterable[Term]) -> dict[Term, float]:
    """Q = {w_qj}: w_qj = 1 if the term is present in the query, else absent
    from the dict (implicit 0) — the query representation from the
    methodology's vector search model.
    """
    return {term: 1.0 for term in set(query_terms)}
