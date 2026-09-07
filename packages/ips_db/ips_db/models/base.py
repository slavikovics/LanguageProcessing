from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Every dense model's vector is zero-padded to this width before storage —
# cosine similarity is invariant to equal zero-padding on both sides, so one
# column width serves any model without a schema change.
MAX_EMBEDDING_DIM = 4096
