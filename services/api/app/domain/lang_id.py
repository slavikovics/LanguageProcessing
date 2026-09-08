
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
    precision: float
    recall: float
    f1: float
    mean_elapsed_ms: float
    confusion: dict[str, dict[str, int]]


def build_confusion_matrix(actual_predicted_pairs: list[tuple[str, str]]) -> dict[str, dict[str, int]]:
    confusion: dict[str, dict[str, int]] = {}
    for actual, predicted in actual_predicted_pairs:
        row = confusion.setdefault(actual, {})
        row[predicted] = row.get(predicted, 0) + 1
    return confusion


def macro_precision_recall_f1(confusion: dict[str, dict[str, int]]) -> tuple[float, float, float]:
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
