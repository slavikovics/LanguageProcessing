
from __future__ import annotations

import math
from typing import Hashable, Mapping

Term = Hashable


def dot_product(a: Mapping[Term, float], b: Mapping[Term, float]) -> float:
    common = a.keys() & b.keys()
    return sum(a[term] * b[term] for term in common)


def euclidean_norm(vector: Mapping[Term, float]) -> float:
    return math.sqrt(sum(weight * weight for weight in vector.values()))


def cosine_similarity(a: Mapping[Term, float], b: Mapping[Term, float]) -> float:
    norm_a = euclidean_norm(a)
    norm_b = euclidean_norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product(a, b) / (norm_a * norm_b)


def manhattan_distance(a: Mapping[Term, float], b: Mapping[Term, float]) -> float:
    keys = a.keys() | b.keys()
    return sum(abs(a.get(term, 0.0) - b.get(term, 0.0)) for term in keys)


def rank_documents(
    query_vector: Mapping[Term, float],
    document_vectors: Mapping[Hashable, Mapping[Term, float]],
) -> list[tuple[Hashable, float]]:
    scored = [
        (doc_id, cosine_similarity(query_vector, vector))
        for doc_id, vector in document_vectors.items()
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
