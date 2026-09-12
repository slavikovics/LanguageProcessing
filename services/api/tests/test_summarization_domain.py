from types import SimpleNamespace

from app.domain.summarization import SelectedSentence, SummaryOutcome, summarize_run


def test_summary_outcome_summary_text_joins_sentences_in_order():
    outcome = SummaryOutcome(
        method="algorithmic",
        sentences=[
            SelectedSentence(index=0, text="First sentence.", weight=0.9),
            SelectedSentence(index=2, text="Third sentence.", weight=0.7),
        ],
        total_sentences=4,
        elapsed_ms=12.5,
    )
    assert outcome.summary_text == "First sentence. Third sentence."


def test_summary_outcome_compression_ratio():
    outcome = SummaryOutcome(
        method="textrank",
        sentences=[SelectedSentence(index=0, text="s", weight=1.0)],
        total_sentences=4,
        elapsed_ms=1.0,
        document_chars=4,
    )
    assert outcome.compression_ratio == 0.25


def test_summary_outcome_compression_ratio_handles_zero_document_chars():
    outcome = SummaryOutcome(method="textrank", sentences=[], total_sentences=0, elapsed_ms=1.0)
    assert outcome.compression_ratio == 0.0


def _fake_summary(
    *,
    elapsed_ms: float,
    total_sentences: int,
    selected_count: int,
    summary_text: str = "",
    total_chars: int = 0,
):
    return SimpleNamespace(
        elapsed_ms=elapsed_ms,
        total_sentences=total_sentences,
        summary_sentence_indices=list(range(selected_count)),
        summary_text=summary_text,
        total_chars=total_chars,
    )


def test_summarize_run_averages_metrics_across_documents():
    summaries = [
        _fake_summary(
            elapsed_ms=10.0, total_sentences=20, selected_count=10,
            summary_text="x" * 50, total_chars=100,
        ),
        _fake_summary(
            elapsed_ms=30.0, total_sentences=10, selected_count=10,
            summary_text="y" * 80, total_chars=80,
        ),
    ]
    summary = summarize_run(run_id=1, method="algorithmic", summaries=summaries)
    assert summary.documents_summarized == 2
    assert summary.mean_elapsed_ms == 20.0
    assert summary.mean_compression_ratio == (0.5 + 1.0) / 2
    assert summary.mean_sentence_count == 10.0


def test_summarize_run_handles_empty_run():
    summary = summarize_run(run_id=1, method="algorithmic", summaries=[])
    assert summary.documents_summarized == 0
    assert summary.mean_elapsed_ms == 0.0
    assert summary.mean_compression_ratio == 0.0
