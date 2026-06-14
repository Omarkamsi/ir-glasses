from compare_models import disruption_threshold


def test_threshold_linear_interpolation():
    levels = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    rates = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0]    # crosses 0.5 between 0.4 and 0.6
    assert abs(disruption_threshold(levels, rates) - 0.5) < 1e-6


def test_threshold_none_when_never_crosses():
    assert disruption_threshold([0.0, 1.0], [1.0, 1.0]) is None
