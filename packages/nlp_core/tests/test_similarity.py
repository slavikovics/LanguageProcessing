import math

from nlp_core import similarity


def test_cosine_similarity_identical_vectors_is_one():
    vec = {"cat": 0.6, "dog": 0.8}
    assert math.isclose(similarity.cosine_similarity(vec, vec), 1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert similarity.cosine_similarity({"cat": 1.0}, {"dog": 1.0}) == 0.0


def test_cosine_similarity_zero_vector_is_zero_not_nan():
    assert similarity.cosine_similarity({"cat": 0.0}, {"cat": 1.0}) == 0.0


def test_rank_documents_orders_by_similarity_descending():
    # Single-term vectors are collinear regardless of magnitude (cosine only
    # measures angle), so this needs a second dimension for d1 vs d2 to
    # actually differ in *direction*, not just scale.
    query = {"cat": 1.0}
    docs = {
        "d1": {"cat": 0.1, "dog": 0.9},
        "d2": {"cat": 0.9, "dog": 0.1},
        "d3": {"dog": 1.0},
    }
    ranked = similarity.rank_documents(query, docs)
    assert [doc_id for doc_id, _ in ranked] == ["d2", "d1", "d3"]
