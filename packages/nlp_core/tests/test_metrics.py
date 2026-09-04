import math

from nlp_core import metrics

RANKED = ["d1", "d2", "d3", "d4", "d5"]
RELEVANT = {"d2", "d4", "d5"}


def test_precision_at_k():
    assert metrics.precision_at_k(RANKED, RELEVANT, 2) == 0.5
    assert metrics.precision_at_k(RANKED, RELEVANT, 5) == 0.6


def test_precision_at_k_zero_k():
    assert metrics.precision_at_k(RANKED, RELEVANT, 0) == 0.0


def test_recall_at_k():
    assert math.isclose(metrics.recall_at_k(RANKED, RELEVANT, 2), 1 / 3)
    assert metrics.recall_at_k(RANKED, RELEVANT, 5) == 1.0


def test_f1_score_zero_when_both_zero():
    assert metrics.f1_score(0.0, 0.0) == 0.0


def test_f1_score_known_value():
    assert math.isclose(metrics.f1_score(0.5, 0.5), 0.5)


def test_average_precision_known_value():
    # relevant hits at ranks 2, 4, 5 -> precisions 1/2, 2/4, 3/5
    expected = (0.5 + 0.5 + 0.6) / 3
    assert math.isclose(metrics.average_precision(RANKED, RELEVANT), expected)


def test_mean_average_precision_averages_runs():
    runs = [(RANKED, RELEVANT), (RANKED, RELEVANT)]
    assert math.isclose(
        metrics.mean_average_precision(runs), metrics.average_precision(RANKED, RELEVANT)
    )


def test_mean_average_precision_empty_runs_is_zero():
    assert metrics.mean_average_precision([]) == 0.0


def test_r_precision():
    # |relevant| = 3 -> precision at rank 3
    assert math.isclose(metrics.r_precision(RANKED, RELEVANT), 1 / 3)


def test_interpolated_precision_recall_endpoints():
    curve = metrics.interpolated_precision_recall(RANKED, RELEVANT)
    levels = [level for level, _ in curve]
    assert levels == [i / 10 for i in range(11)]
    assert curve[0][1] == max(precision for _, precision in curve)


def test_micro_average_precision_recall_known_value():
    # run 1: 2 hits / 5 retrieved, 2 hits / 3 relevant
    # run 2: 1 hit / 3 retrieved, 1 hit / 2 relevant
    runs = [
        (["d1", "d2", "d3", "d4", "d5"], {"d1", "d2", "d9"}),
        (["e1", "e2", "e3"], {"e1", "e9"}),
    ]
    precision, recall = metrics.micro_average_precision_recall(runs)
    # total hits=3, total retrieved=8, total relevant=5
    assert math.isclose(precision, 3 / 8)
    assert math.isclose(recall, 3 / 5)


def test_micro_average_precision_recall_empty_runs_is_zero():
    assert metrics.micro_average_precision_recall([]) == (0.0, 0.0)


def test_micro_average_differs_from_macro_average():
    # A query with a small denominator shouldn't dominate a micro-average
    # the way it would a simple mean of per-query ratios.
    runs = [(["a1"], {"a1"}), (["b1", "b2", "b3", "b4"], {"b1"})]
    precision, _ = metrics.micro_average_precision_recall(runs)
    macro_precision = (1.0 + 0.25) / 2
    assert not math.isclose(precision, macro_precision)
    assert math.isclose(precision, 2 / 5)


def test_metrics_handle_no_relevant_documents_without_error():
    assert metrics.precision_at_k(RANKED, set(), 3) == 0.0
    assert metrics.recall_at_k(RANKED, set(), 3) == 0.0
    assert metrics.average_precision(RANKED, set()) == 0.0
    assert metrics.r_precision(RANKED, set()) == 0.0
    assert metrics.interpolated_precision_recall(RANKED, set()) == [
        (i / 10, 0.0) for i in range(11)
    ]
