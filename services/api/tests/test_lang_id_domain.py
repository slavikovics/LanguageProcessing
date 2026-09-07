import pytest

from app.domain.lang_id import (
    LangIdError,
    build_confusion_matrix,
    macro_precision_recall_f1,
    split_train_test,
    summarize_results,
)


def test_build_confusion_matrix_counts_actual_predicted_pairs():
    pairs = [("en", "en"), ("en", "ru"), ("ru", "ru"), ("ru", "ru")]
    assert build_confusion_matrix(pairs) == {"en": {"en": 1, "ru": 1}, "ru": {"ru": 2}}


def test_macro_precision_recall_f1_perfect_classifier():
    confusion = {"en": {"en": 2}, "ru": {"ru": 2}}
    precision, recall, f1 = macro_precision_recall_f1(confusion)
    assert precision == 1.0
    assert recall == 1.0
    assert f1 == 1.0


def test_macro_precision_recall_f1_averages_per_language():
    # en: 1 correct, 1 misclassified as ru -> precision 1/1=1.0 (no false ru->en), recall 1/2=0.5
    # ru: 2 correct, 0 misclassified, but 1 en misclassified as ru -> precision 2/3, recall 2/2=1.0
    confusion = {"en": {"en": 1, "ru": 1}, "ru": {"ru": 2}}
    precision, recall, f1 = macro_precision_recall_f1(confusion)
    assert precision == (1.0 + 2 / 3) / 2
    assert recall == (0.5 + 1.0) / 2
    assert f1 > 0.0


def test_macro_precision_recall_f1_empty_confusion():
    assert macro_precision_recall_f1({}) == (0.0, 0.0, 0.0)


def test_summarize_results_includes_precision_recall_f1():
    pairs = [("en", "en"), ("en", "ru"), ("ru", "ru"), ("ru", "ru")]
    summary = summarize_results(
        run_id=1, method="frequent_words", actual_predicted_pairs=pairs, elapsed_ms_values=[1.0, 2.0, 3.0, 4.0]
    )
    assert summary.accuracy == 0.75
    assert 0.0 < summary.precision <= 1.0
    assert 0.0 < summary.recall <= 1.0
    assert 0.0 < summary.f1 <= 1.0
    assert summary.mean_elapsed_ms == 2.5


def test_split_train_test_is_stratified_and_covers_every_document():
    by_language = {"en": list(range(1, 11)), "fr": list(range(101, 106))}
    train_ids, test_ids = split_train_test(by_language, test_ratio=0.2, seed=0)

    assert set(train_ids) | set(test_ids) == set(range(1, 11)) | set(range(101, 106))
    assert set(train_ids) & set(test_ids) == set()
    en_test = [i for i in test_ids if i < 100]
    fr_test = [i for i in test_ids if i >= 100]
    assert len(en_test) == 2  # round(10 * 0.2)
    assert len(fr_test) == 1  # round(5 * 0.2), clamped to at least 1


def test_split_train_test_single_document_language_goes_entirely_to_train():
    train_ids, test_ids = split_train_test({"en": [1]}, test_ratio=0.2, seed=0)
    assert train_ids == [1]
    assert test_ids == []


def test_split_train_test_rejects_out_of_range_ratio():
    with pytest.raises(LangIdError):
        split_train_test({"en": [1, 2]}, test_ratio=1.0)
    with pytest.raises(LangIdError):
        split_train_test({"en": [1, 2]}, test_ratio=0.0)
