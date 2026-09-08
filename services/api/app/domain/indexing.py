
from __future__ import annotations

from dataclasses import dataclass


class IndexingError(ValueError):
    pass


class IndexingCancelled(Exception):
    pass


@dataclass(frozen=True)
class IndexingSummary:
    collection_id: int
    documents_indexed: int
    terms_indexed: int


CHUNK_TARGET_WORDS = 350
CHUNK_OVERLAP_WORDS = 40


def chunk_text(
    text: str,
    *,
    target_words: int = CHUNK_TARGET_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= target_words:
        return [text.strip()]

    step = max(1, target_words - overlap_words)
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start : start + target_words]))
        if start + target_words >= len(words):
            break
        start += step
    return chunks
