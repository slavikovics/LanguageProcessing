
from __future__ import annotations

from collections import Counter

from .tokenization import simple_word_tokenize

DEFAULT_TOP_N = 300
DEFAULT_MAX_PENALTY = DEFAULT_TOP_N


def build_profile(texts: list[str], *, top_n: int = DEFAULT_TOP_N) -> list[str]:
    counts = Counter(word for text in texts for word in simple_word_tokenize(text))
    return [word for word, _ in counts.most_common(top_n)]


def out_of_place_distance(
    profile: list[str], document_text: str, *, max_penalty: int = DEFAULT_MAX_PENALTY
) -> float:
    doc_counts = Counter(simple_word_tokenize(document_text))
    doc_rank = {word: rank for rank, (word, _) in enumerate(doc_counts.most_common())}
    total = 0
    for profile_rank, word in enumerate(profile):
        document_rank = doc_rank.get(word)
        total += abs(profile_rank - document_rank) if document_rank is not None else max_penalty
    return float(total)
