
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SOURCE_LANGUAGE = "en"
DEFAULT_TARGET_LANGUAGE = "fr"


class TranslationError(ValueError):
    pass


@dataclass(frozen=True)
class TranslationRunSummary:
    run_id: int
    source_lang: str
    target_lang: str
    documents_translated: int
    mean_elapsed_ms: float
    mean_word_count: float
    mean_translated_word_count: float
    mean_translated_text_word_count: float
    mean_coverage_ratio: float


def summarize_translation_run(
    *, run_id: int, source_lang: str, target_lang: str, runs: list
) -> TranslationRunSummary:
    if not runs:
        return TranslationRunSummary(
            run_id=run_id,
            source_lang=source_lang,
            target_lang=target_lang,
            documents_translated=0,
            mean_elapsed_ms=0.0,
            mean_word_count=0.0,
            mean_translated_word_count=0.0,
            mean_translated_text_word_count=0.0,
            mean_coverage_ratio=0.0,
        )
    count = len(runs)
    coverage_values = [(run.translated_word_count / run.word_count) if run.word_count else 0.0 for run in runs]
    return TranslationRunSummary(
        run_id=run_id,
        source_lang=source_lang,
        target_lang=target_lang,
        documents_translated=count,
        mean_elapsed_ms=sum(run.elapsed_ms for run in runs) / count,
        mean_word_count=sum(run.word_count for run in runs) / count,
        mean_translated_word_count=sum(run.translated_word_count for run in runs) / count,
        mean_translated_text_word_count=sum(run.translated_text_word_count for run in runs) / count,
        mean_coverage_ratio=sum(coverage_values) / count,
    )
