"""Pure search rules: query validation and the snippet-building heuristic.
Scoring itself lives in nlp_core (cosine) via nlp-service; this module only
holds logic that has no business being an HTTP call — validating a query and
picking which slice of a document's text to show in the results list.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Sequence

MAX_TOP_K = 100
DEFAULT_TOP_K = 10
SNIPPET_MAX_CHARS = 320


class SearchError(ValueError):
    pass


@dataclass(frozen=True)
class SearchQueryConfig:
    collection_id: int
    text: str
    top_k: int


def build_search_query_config(
    *, collection_id: int, text: str, top_k: int = DEFAULT_TOP_K
) -> SearchQueryConfig:
    cleaned = text.strip()
    if not cleaned:
        raise SearchError("query text must not be empty")
    if not (1 <= top_k <= MAX_TOP_K):
        raise SearchError(f"top_k must be between 1 and {MAX_TOP_K}")
    return SearchQueryConfig(collection_id=collection_id, text=cleaned, top_k=top_k)


def build_snippet(
    text: str, focus_words: Sequence[str], *, max_chars: int = SNIPPET_MAX_CHARS
) -> str:
    """A window of `text` centered on the first occurrence of any of
    `focus_words` (case-insensitive substring match on the raw query words —
    not the lemmas, so inflected surface forms still anchor the snippet).
    Falls back to the start of the document when nothing matches literally.
    """
    lowered = text.lower()
    position: int | None = None
    for word in focus_words:
        idx = lowered.find(word.lower())
        if idx != -1 and (position is None or idx < position):
            position = idx

    start = 0 if position is None else max(0, position - max_chars // 3)
    end = min(len(text), start + max_chars)
    snippet = text[start:end].strip()
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


@dataclass(frozen=True)
class SearchHit:
    document_id: int
    title: str
    url: str | None
    fetched_at: dt.datetime
    rank: int
    score: float
    snippet: str
    matched_terms: list[str]


@dataclass(frozen=True)
class SearchResponse:
    query_id: int
    search_run_id: int
    query_text: str
    model: str
    model_label: str
    hits: list[SearchHit]
