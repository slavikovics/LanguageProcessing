
from __future__ import annotations

from collections import Counter

from . import similarity


def build_profile(texts: list[str]) -> dict[str, float]:
    counts = Counter(ch for text in texts for ch in text.lower() if ch.isalpha())
    total = sum(counts.values())
    if total == 0:
        return {}
    return {ch: count / total for ch, count in counts.items()}


def distance(profile: dict[str, float], document_text: str) -> float:
    document_profile = build_profile([document_text])
    return similarity.manhattan_distance(profile, document_profile)
