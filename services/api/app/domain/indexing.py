"""Pure indexing rules — no I/O. Mirrors app.domain.crawl_jobs: validation
errors and result shapes live here, orchestration lives in application/.
"""

from __future__ import annotations

from dataclasses import dataclass


class IndexingError(ValueError):
    pass


class IndexingCancelled(Exception):
    """Raised from inside IndexingService._run to unwind out of the
    tfidf/embedding pass loops the moment a running job notices it's been
    cancelled (see IndexJobRepository.request_cancel) — caught in run_job,
    which then simply stops instead of finalizing to "completed"/"failed"
    and clobbering the "cancelled" status already written to the DB."""


@dataclass(frozen=True)
class IndexingSummary:
    collection_id: int
    documents_indexed: int
    terms_indexed: int


# Word-based, not token-based: measuring real subword-token length would
# mean an extra nlp-service round trip per document just to find out how
# long it is. ~350 words comfortably fits multilingual-e5-small's 512-token
# window (see nlp-service's app/embeddings.py) even after subword growth and
# the "passage: " prefix. Overlap keeps a sentence that would otherwise
# straddle a chunk boundary fully readable in at least one chunk.
CHUNK_TARGET_WORDS = 350
CHUNK_OVERLAP_WORDS = 40


def chunk_text(
    text: str,
    *,
    target_words: int = CHUNK_TARGET_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
    """Splits `text` into overlapping, roughly `target_words`-sized pieces.

    A document under the target size is returned as a single chunk
    unchanged — this is the common case and keeps short documents from
    paying any chunking overhead. Splitting on whitespace-delimited words
    (not sentences) avoids a spaCy dependency here purely for chunk
    boundaries; the overlap window means an occasional mid-sentence cut
    still leaves that sentence intact in a neighboring chunk.
    """
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
