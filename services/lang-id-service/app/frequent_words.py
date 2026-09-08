
from __future__ import annotations

import time

from nlp_core import frequent_words as fw


def build_profile(texts: list[str], *, top_n: int) -> list[str]:
    return fw.build_profile(texts, top_n=top_n)


def identify(top_words_by_language: dict[str, list[str]], text: str) -> dict:
    started = time.perf_counter()
    distances = {
        language: fw.out_of_place_distance(profile, text)
        for language, profile in top_words_by_language.items()
    }
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "distances": distances,
        "predicted_language": min(distances, key=distances.get),
        "elapsed_ms": elapsed_ms,
    }
