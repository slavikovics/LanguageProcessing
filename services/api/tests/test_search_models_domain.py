import pytest

from app.infrastructure.embedding_padding import pad_to_max_dim
from ips_db import MAX_EMBEDDING_DIM


def test_pad_to_max_dim_appends_zeros():
    padded = pad_to_max_dim([1.0, 2.0, 3.0])
    assert len(padded) == MAX_EMBEDDING_DIM
    assert padded[:3] == [1.0, 2.0, 3.0]
    assert all(v == 0.0 for v in padded[3:])


def test_pad_to_max_dim_exact_length_is_unchanged():
    vector = [0.1] * MAX_EMBEDDING_DIM
    assert pad_to_max_dim(vector) == vector


def test_pad_to_max_dim_rejects_oversized_vector():
    with pytest.raises(ValueError):
        pad_to_max_dim([0.0] * (MAX_EMBEDDING_DIM + 1))


def test_pad_to_max_dim_preserves_cosine_similarity():

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        return dot / (norm_a * norm_b)

    a = [0.6, 0.8, 0.0]
    b = [0.0, 0.6, 0.8]
    assert cosine(pad_to_max_dim(a), pad_to_max_dim(b)) == pytest.approx(cosine(a, b))
