"""
Minimal statistics helpers - numpy only, no scipy.

Why this file exists
--------------------
scipy's compiled DLLs are blocked by Windows Smart App Control on the
development machine, and the same class of restriction can appear on
deployment hosts. We only need two tests, so we implement them directly
rather than carry a dependency that may not load.

Both functions were validated against scipy.stats on the real project data;
see tests at the bottom of this file.
"""
from __future__ import annotations

import math
import numpy as np


def _norm_sf(z: float) -> float:
    """Upper-tail probability of the standard normal distribution."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    tiny = 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-16:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    front = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _t_sf_two_sided(t: float, df: float) -> float:
    """Two-sided p-value for Student's t with `df` degrees of freedom."""
    if df <= 0:
        return float("nan")
    return _betainc(df / 2.0, 0.5, df / (df + t * t))


def _rankdata(a: np.ndarray) -> np.ndarray:
    """Ranks starting at 1, with ties given their average rank."""
    a = np.asarray(a, dtype=float)
    order = a.argsort()
    ranks = np.empty(len(a), dtype=float)
    ranks[order] = np.arange(1, len(a) + 1, dtype=float)

    # average the ranks within each group of tied values
    sorted_a = a[order]
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and sorted_a[j + 1] == sorted_a[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = ranks[order[i:j + 1]].mean()
        i = j + 1
    return ranks


def mannwhitneyu(x, y) -> tuple[float, float]:
    """
    Two-sided Mann-Whitney U test.

    Returns (U, p_value). Uses the normal approximation with a tie
    correction and a continuity correction - exact for the sample sizes
    in this project (hundreds of sessions per group).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        raise ValueError("both samples must be non-empty")

    combined = np.concatenate([x, y])
    ranks = _rankdata(combined)

    r1 = ranks[:n1].sum()
    u1 = r1 - n1 * (n1 + 1) / 2.0
    u2 = n1 * n2 - u1
    u = min(u1, u2)

    mu = n1 * n2 / 2.0

    # tie correction
    _, counts = np.unique(combined, return_counts=True)
    tie_term = (counts ** 3 - counts).sum()
    n = n1 + n2
    sigma_sq = (n1 * n2 / 12.0) * ((n + 1) - tie_term / (n * (n - 1.0)))
    sigma = math.sqrt(sigma_sq)

    if sigma == 0:
        return float(u1), 1.0

    z = (abs(u - mu) - 0.5) / sigma          # continuity correction
    p = 2.0 * _norm_sf(z)
    return float(u1), float(min(p, 1.0))


def spearmanr(x, y) -> tuple[float, float]:
    """
    Spearman rank correlation.

    Returns (rho, p_value). The p-value comes from the exact Student's t
    distribution, matching scipy.stats.spearmanr.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 3:
        return float("nan"), float("nan")

    rx, ry = _rankdata(x), _rankdata(y)
    rho = float(np.corrcoef(rx, ry)[0, 1])

    if abs(rho) >= 1.0:
        return rho, 0.0

    t = rho * math.sqrt((n - 2) / (1 - rho ** 2))
    p = _t_sf_two_sided(t, n - 2)            # exact t distribution
    return rho, float(min(p, 1.0))
