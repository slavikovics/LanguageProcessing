"""The contract a pluggable search backend implements — see
app/application/search_tfidf.py (TfidfSearchBackend) and
app/application/search_embedding.py (EmbeddingSearchBackend). Not enforced
at runtime (Protocol is structural), but documents what a *third* backend
kind would need to provide; a third model that reuses an existing kind
(another dense-embedding checkpoint) needs no new backend at all — only a
new `search_models` registry row (see migrations/versions/0005*).
"""

from __future__ import annotations

from typing import Protocol

from ips_db import Collection, SearchModel


class SearchBackend(Protocol):
    async def rank(
        self, *, collection: Collection, text: str, model_row: SearchModel
    ) -> list[tuple[int, float]]:
        """Ranked (document_id, score) pairs for every scored document, best
        first — not just top_k, since rank-sensitive metrics like AP/
        R-precision/the 11-point curve need the full ranking. "Matched
        terms" for the UI is computed separately in SearchService, from the
        indexed TF-IDF vocabulary — it's a lexical-overlap fact about a
        document, independent of which backend ranked it, so every backend
        (including dense-embedding ones with no discrete "matched term"
        concept of their own) gets it for free."""
        ...
