import math

from app.domain.metrics import average_curves


def test_average_curves_elementwise_mean():
    curve_a = [(0.0, 1.0), (0.5, 0.5), (1.0, 0.0)]
    curve_b = [(0.0, 0.0), (0.5, 1.0), (1.0, 1.0)]
    averaged = average_curves([curve_a, curve_b])
    assert averaged == [(0.0, 0.5), (0.5, 0.75), (1.0, 0.5)]


def test_average_curves_single_curve_is_unchanged():
    curve = [(0.0, 0.8), (1.0, 0.2)]
    assert average_curves([curve]) == curve


def test_average_curves_empty_input():
    assert average_curves([]) == []
