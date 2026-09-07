"""Pure language-ID rules — no I/O. Mirrors app.domain.indexing: validation
errors and result shapes live here, orchestration lives in application/.

Contract shared by all three methods: every identify call returns a
`distances` mapping where LOWER means closer, so `min(distances, key=get)`
is the one argmin rule that works for frequent-words, alphabetic, and
neural alike — lang-id-service's neural endpoint converts its softmax
probability to `1 - probability` before responding so this holds for it too.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

METHODS: tuple[str, ...] = ("frequent_words", "alphabetic", "neural")


class LangIdError(ValueError):
    pass


@dataclass(frozen=True)
class IdentificationOutcome:
    method: str
    predicted_language: str
    distances: dict[str, float]
    elapsed_ms: float


@dataclass(frozen=True)
class LangIdRunSummary:
    run_id: int
    method: str
    documents_evaluated: int
    accuracy: float
    # Macro-averaged over every language seen as either actual or predicted
    # (sklearn's default for average="macro"): the mean of each language's
    # own precision/recall/F1, so a rare language counts as much as a common
    # one rather than being drowned out by document volume.
    precision: float
    recall: float
    f1: float
    mean_elapsed_ms: float
    # {actual_language: {predicted_language: count}}
    confusion: dict[str, dict[str, int]]


def build_confusion_matrix(actual_predicted_pairs: list[tuple[str, str]]) -> dict[str, dict[str, int]]:
    confusion: dict[str, dict[str, int]] = {}
    for actual, predicted in actual_predicted_pairs:
        row = confusion.setdefault(actual, {})
        row[predicted] = row.get(predicted, 0) + 1
    return confusion


def macro_precision_recall_f1(confusion: dict[str, dict[str, int]]) -> tuple[float, float, float]:
    """Per-language precision/recall/F1 from a confusion matrix, then
    averaged unweighted across languages (macro-average)."""
    languages: set[str] = set(confusion.keys())
    for row in confusion.values():
        languages.update(row.keys())
    if not languages:
        return 0.0, 0.0, 0.0

    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []
    for language in languages:
        row = confusion.get(language, {})
        true_positive = row.get(language, 0)
        false_negative = sum(count for predicted, count in row.items() if predicted != language)
        false_positive = sum(
            other_row.get(language, 0) for actual, other_row in confusion.items() if actual != language
        )
        precision = (
            true_positive / (true_positive + false_positive) if (true_positive + false_positive) > 0 else 0.0
        )
        recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

    count = len(languages)
    return sum(precisions) / count, sum(recalls) / count, sum(f1s) / count


def split_train_test(
    document_ids_by_language: dict[str, list[int]], *, test_ratio: float, seed: int | None = None
) -> tuple[list[int], list[int]]:
    """Stratified per-language train/test split: shuffles each language's
    document ids independently and assigns `test_ratio` of them to test, the
    rest to train — stratifying keeps every language represented on both
    sides regardless of how lopsided the labeled counts are. A language
    with only one confirmed document goes entirely to train (a profile
    needs at least one; a lone document can't usefully test one anyway)."""
    if not 0 < test_ratio < 1:
        raise LangIdError("test_ratio must be between 0 and 1 (exclusive)")

    rng = random.Random(seed)
    train_ids: list[int] = []
    test_ids: list[int] = []
    for ids in document_ids_by_language.values():
        shuffled = list(ids)
        rng.shuffle(shuffled)
        if len(shuffled) < 2:
            train_ids.extend(shuffled)
            continue
        test_count = max(1, min(round(len(shuffled) * test_ratio), len(shuffled) - 1))
        test_ids.extend(shuffled[:test_count])
        train_ids.extend(shuffled[test_count:])
    return train_ids, test_ids


def summarize_results(
    *,
    run_id: int,
    method: str,
    actual_predicted_pairs: list[tuple[str, str]],
    elapsed_ms_values: list[float],
) -> LangIdRunSummary:
    total = len(actual_predicted_pairs)
    correct = sum(1 for actual, predicted in actual_predicted_pairs if actual == predicted)
    accuracy = correct / total if total else 0.0
    mean_elapsed_ms = sum(elapsed_ms_values) / len(elapsed_ms_values) if elapsed_ms_values else 0.0
    confusion = build_confusion_matrix(actual_predicted_pairs)
    precision, recall, f1 = macro_precision_recall_f1(confusion)
    return LangIdRunSummary(
        run_id=run_id,
        method=method,
        documents_evaluated=total,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        mean_elapsed_ms=mean_elapsed_ms,
        confusion=confusion,
    )
