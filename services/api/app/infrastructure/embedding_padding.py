
from __future__ import annotations

from ips_db import MAX_EMBEDDING_DIM


def pad_to_max_dim(vector: list[float]) -> list[float]:
    if len(vector) > MAX_EMBEDDING_DIM:
        raise ValueError(
            f"vector dimension {len(vector)} exceeds MAX_EMBEDDING_DIM {MAX_EMBEDDING_DIM}"
        )
    return vector + [0.0] * (MAX_EMBEDDING_DIM - len(vector))
