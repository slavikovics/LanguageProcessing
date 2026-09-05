"""Zero-padding to the shared document_embeddings column width. Cosine
similarity is invariant to appending equal-length zero runs to both
compared vectors (no extra dot-product terms, no norm change), and vectors
are only ever compared within one search_model_id, so a single fixed-width
pgvector column serves any number of dense models without a migration per
model — see ips_db.models.MAX_EMBEDDING_DIM.
"""

from __future__ import annotations

from ips_db import MAX_EMBEDDING_DIM


def pad_to_max_dim(vector: list[float]) -> list[float]:
    if len(vector) > MAX_EMBEDDING_DIM:
        raise ValueError(
            f"vector dimension {len(vector)} exceeds MAX_EMBEDDING_DIM {MAX_EMBEDDING_DIM}"
        )
    return vector + [0.0] * (MAX_EMBEDDING_DIM - len(vector))
