"""LR2's frequent-words language-identification method: a language's profile
is its ranked list of most frequent words, and distance to a document is the
Cavnar-Trenkle "out-of-place" rank distance, applied to whole words rather
than the character n-grams of their original 1994 paper (this variant's
assigned method is word-level, not n-gram-based).
"""

from __future__ import annotations

from collections import Counter

from .tokenization import simple_word_tokenize

DEFAULT_TOP_N = 300
# Charged for a profile word absent from the document entirely — must be at
# least DEFAULT_TOP_N so "missing" is always worse than any in-document rank
# mismatch, matching the original method's treatment of a no-match n-gram.
DEFAULT_MAX_PENALTY = DEFAULT_TOP_N


def build_profile(texts: list[str], *, top_n: int = DEFAULT_TOP_N) -> list[str]:
    """Ranked list (most frequent first) of the top_n most frequent words
    across the whole training corpus for one language."""
    counts = Counter(word for text in texts for word in simple_word_tokenize(text))
    return [word for word, _ in counts.most_common(top_n)]


def out_of_place_distance(
    profile: list[str], document_text: str, *, max_penalty: int = DEFAULT_MAX_PENALTY
) -> float:
    """Sum, over each word in `profile`, of |its rank in profile - its rank
    in the document's own frequency ranking| — charging max_penalty for a
    profile word the document doesn't contain at all. Lower is closer."""
    doc_counts = Counter(simple_word_tokenize(document_text))
    doc_rank = {word: rank for rank, (word, _) in enumerate(doc_counts.most_common())}
    total = 0
    for profile_rank, word in enumerate(profile):
        document_rank = doc_rank.get(word)
        total += abs(profile_rank - document_rank) if document_rank is not None else max_penalty
    return float(total)
