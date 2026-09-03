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
    query = {"cat": 1.0}
    docs = {
        "d1": {"cat": 0.1},
        "d2": {"cat": 0.9},
        "d3": {"dog": 1.0},
    }
    ranked = similarity.rank_documents(query, docs)
    assert [doc_id for doc_id, _ in ranked] == ["d2", "d1", "d3"]
