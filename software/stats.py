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
