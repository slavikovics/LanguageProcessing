
from __future__ import annotations

from dataclasses import dataclass

METHODS: tuple[str, ...] = ("algorithmic", "textrank", "embeddings")


class SummarizationError(ValueError):
    pass


@dataclass(frozen=True)
class SelectedSentence:
    index: int
    text: str
    weight: float


@dataclass(frozen=True)
class SummaryOutcome:
    method: str
    sentences: list[SelectedSentence]
    total_sentences: int
    elapsed_ms: float
    document_chars: int = 0

    @property
    def summary_text(self) -> str:
        return " ".join(sentence.text for sentence in self.sentences)

    @property
    def compression_ratio(self) -> float:
        """Character length of the extracted summary relative to the source
        document. Sentence-count ratio would be identical across methods
        whenever they target the same sentence_count, so it can't distinguish
        methods — character length varies with which (shorter/longer)
        sentences each method actually picked."""
        if self.document_chars <= 0:
            return 0.0
        return len(self.summary_text) / self.document_chars


@dataclass(frozen=True)
class SummarizationRunSummary:
    run_id: int
    method: str
    documents_summarized: int
    mean_elapsed_ms: float
    mean_compression_ratio: float
    mean_sentence_count: float


def summarize_run(
    *, run_id: int, method: str, summaries: list
) -> SummarizationRunSummary:
    if not summaries:
        return SummarizationRunSummary(
            run_id=run_id,
            method=method,
            documents_summarized=0,
            mean_elapsed_ms=0.0,
            mean_compression_ratio=0.0,
            mean_sentence_count=0.0,
        )
    elapsed_values = [summary.elapsed_ms for summary in summaries]
    compression_values = [
        (len(summary.summary_text) / summary.total_chars) if summary.total_chars else 0.0
        for summary in summaries
    ]
    sentence_counts = [len(summary.summary_sentence_indices) for summary in summaries]
    count = len(summaries)
    return SummarizationRunSummary(
        run_id=run_id,
        method=method,
        documents_summarized=count,
        mean_elapsed_ms=sum(elapsed_values) / count,
        mean_compression_ratio=sum(compression_values) / count,
        mean_sentence_count=sum(sentence_counts) / count,
    )
