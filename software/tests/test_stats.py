from stats import wilson_interval, baseline_correct


def test_baseline_correct_normalizes_to_clean():
    # clean (first) rate is the baseline -> becomes 1.0; others scale relative to it
    assert baseline_correct([0.8, 0.4, 0.0]) == [1.0, 0.5, 0.0]


def test_baseline_correct_zero_baseline_passthrough():
    assert baseline_correct([0.0, 0.0]) == [0.0, 0.0]


def test_wilson_midpoint_and_bounds():
    lo, hi = wilson_interval(5, 10)          # 50% of 10
    assert 0.0 <= lo < 0.5 < hi <= 1.0
    assert round((lo + hi) / 2, 2) == 0.5    # symmetric at p=0.5


def test_wilson_all_success_not_one():
    lo, hi = wilson_interval(10, 10)         # 100% -> upper near 1, lower < 1
    assert hi <= 1.0 and lo < 1.0


def test_wilson_zero_n():
    assert wilson_interval(0, 0) == (0.0, 1.0)
