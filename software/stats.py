"""stats.py — confidence intervals for binomial proportions (success rates)."""
import math


def wilson_interval(successes, n, z=1.96):
    """95% Wilson score interval for a proportion. Returns (lo, hi) in [0, 1].

    The Wilson interval behaves well for small n and for rates near 0 or 1, which is
    exactly where the naive normal interval breaks down — so it is the right choice
    for detection/recognition rates measured over a handful of subjects.
    """
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def baseline_correct(rates):
    """Normalize a sequence of recognition rates by the clean baseline (rates[0]).

    Isolates the *disruption* effect from the recogniser's own error on clean images:
    the clean rate maps to 1.0 and the rest scale relative to it. If the baseline is 0,
    the rates are returned unchanged.
    """
    if not rates or rates[0] <= 0:
        return list(rates)
    base = rates[0]
    return [min(1.0, r / base) for r in rates]
