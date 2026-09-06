"""The contract a pluggable search backend implements (TfidfSearchBackend,
EmbeddingSearchBackend). A model that reuses an existing backend kind needs
only a new search_models registry row, not a new backend.
"""

from __future__ import annotations

from typing import Protocol

from ips_db import Collection, SearchModel


class SearchBackend(Protocol):
    async def rank(
        self, *, collection: Collection, text: str, model_row: SearchModel
    ) -> list[tuple[int, float]]:
        """Ranked (document_id, score) pairs for every scored document, best
        first — the full ranking, not just top_k, since AP/R-precision/the
        curve need it. Matched terms are computed separately by
        SearchService for every backend, dense-embedding ones included."""
        ...
