
from __future__ import annotations

import time

from nlp_core import alphabetic as alpha


def build_profile(texts: list[str]) -> dict[str, float]:
    return alpha.build_profile(texts)


def identify(profiles_by_language: dict[str, dict[str, float]], text: str) -> dict:
    started = time.perf_counter()
    distances = {
        language: alpha.distance(profile, text) for language, profile in profiles_by_language.items()
    }
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "distances": distances,
        "predicted_language": min(distances, key=distances.get),
        "elapsed_ms": elapsed_ms,
    }
