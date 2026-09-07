"""LR2's alphabetic language-identification method: a language's profile is
its normalized per-character frequency distribution, compared to a document
by Manhattan (L1) distance. Built from `str.isalpha()` characters rather
than a fixed 26-letter alphabet, so French's accented letters (é, è, ç, à,
...) are captured as their own distinguishing signal instead of being
dropped or folded into their unaccented form.
"""

from __future__ import annotations

from collections import Counter

from . import similarity


def build_profile(texts: list[str]) -> dict[str, float]:
    """Normalized per-character frequency distribution over the corpus."""
    counts = Counter(ch for text in texts for ch in text.lower() if ch.isalpha())
    total = sum(counts.values())
    if total == 0:
        return {}
    return {ch: count / total for ch, count in counts.items()}


def distance(profile: dict[str, float], document_text: str) -> float:
    """Manhattan distance between a language profile and one document's own
    character-frequency distribution. Lower is closer."""
    document_profile = build_profile([document_text])
    return similarity.manhattan_distance(profile, document_profile)
