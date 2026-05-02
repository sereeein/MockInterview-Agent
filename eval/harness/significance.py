"""Pure-Python statistics for the harness.

Why no scipy: the eval/ pyproject is intentionally lean (anthropic, pyyaml,
pydantic, rich). All routines below are correct for the small N used in
evaluation runs (N ≤ ~200) and avoid the binary dep.

Provided:
  * wilson_ci          — 95% Wilson interval for a proportion
  * fishers_exact      — two-tailed p-value for a 2x2 contingency table
  * required_n_for_power — sample size per arm to detect p0 vs p1 at given power
"""
from __future__ import annotations

import math
from dataclasses import dataclass


# --------------------------------------------------------------------------- #
# Wilson confidence interval                                                  #
# --------------------------------------------------------------------------- #


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion.

    More accurate than the normal approximation at small N or near 0/1, which
    is exactly the regime we expect when a fix drops failure rate to <5%.
    """
    if n == 0:
        return (0.0, 0.0)
    p_hat = successes / n
    denom = 1 + z * z / n
    center = (p_hat + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p_hat * (1 - p_hat) / n + z * z / (4 * n * n))) / denom
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return (lo, hi)


# --------------------------------------------------------------------------- #
# Fisher's exact test (two-tailed)                                            #
# --------------------------------------------------------------------------- #


def _log_factorial(n: int) -> float:
    return math.lgamma(n + 1)


def _log_hypergeom_pmf(a: int, b: int, c: int, d: int) -> float:
    """log P(table | margins fixed) for 2x2 contingency table:
              col1  col2
       row1:   a     b
       row2:   c     d
    Uses log factorials to stay numerically stable.
    """
    n = a + b + c + d
    return (
        _log_factorial(a + b) + _log_factorial(c + d)
        + _log_factorial(a + c) + _log_factorial(b + d)
        - _log_factorial(n)
        - _log_factorial(a) - _log_factorial(b)
        - _log_factorial(c) - _log_factorial(d)
    )


def fishers_exact(succ_a: int, fail_a: int, succ_b: int, fail_b: int) -> float:
    """Two-tailed Fisher's exact p-value for the 2x2 table:

                 success  failure
       arm A:    succ_a   fail_a
       arm B:    succ_b   fail_b

    Returns p-value of observing a table at least as extreme as the input,
    under the null hypothesis of equal proportions. Uses the standard
    "sum of all tables with probability ≤ observed" definition.
    """
    if min(succ_a, fail_a, succ_b, fail_b) < 0:
        raise ValueError("counts must be non-negative")

    n_a = succ_a + fail_a
    n_b = succ_b + fail_b
    if n_a == 0 or n_b == 0:
        return 1.0

    total_succ = succ_a + succ_b
    total_n = n_a + n_b

    log_p_obs = _log_hypergeom_pmf(succ_a, fail_a, succ_b, fail_b)

    # Iterate every feasible value of succ_a (call it x) given fixed margins.
    lo = max(0, total_succ - n_b)
    hi = min(n_a, total_succ)
    p_value = 0.0
    # Sum probabilities of every table at least as extreme as observed.
    # Comparison uses log-probabilities with a small fudge for FP equality.
    eps = 1e-12
    for x in range(lo, hi + 1):
        a = x
        b = n_a - x
        c = total_succ - x
        d = n_b - (total_succ - x)
        log_p = _log_hypergeom_pmf(a, b, c, d)
        if log_p <= log_p_obs + eps:
            p_value += math.exp(log_p)
    return min(1.0, p_value)


# --------------------------------------------------------------------------- #
# Sample size for two-proportion test                                         #
# --------------------------------------------------------------------------- #


@dataclass
class PowerResult:
    n_per_arm: int
    method: str
    note: str = ""


def required_n_for_power(
    p0: float,
    p1: float,
    *,
    alpha: float = 0.05,
    power: float = 0.8,
) -> PowerResult:
    """Sample size per arm to detect difference between baseline rate p0 and
    target rate p1 with the given alpha (two-sided) and power.

    Uses the standard normal-approximation formula:

       n = ((z_{α/2} √(2 p̄ q̄) + z_β √(p0 q0 + p1 q1))²) / (p0 - p1)²

    where p̄ = (p0 + p1) / 2.

    Caveat: when min(p0, p1, 1-p0, 1-p1) is small (< 0.05) and N would be small,
    the normal approximation under-estimates required N. We flag that case and
    suggest using exact methods (Fisher) — for our use, just bump N up.
    """
    if not (0.0 < p0 < 1.0 and 0.0 < p1 < 1.0):
        # Edge case: if p0 == 0 or p1 == 0 the formula degenerates; pick a safe N.
        return PowerResult(
            n_per_arm=200,
            method="degenerate",
            note=f"p0={p0}, p1={p1}; normal approximation invalid, suggest N=200 + Fisher's exact at analysis time",
        )

    if abs(p0 - p1) < 1e-9:
        return PowerResult(
            n_per_arm=10**9,
            method="degenerate",
            note="p0 == p1; effect size is zero, infinite N required",
        )

    z_alpha = _z_for_two_sided_alpha(alpha)
    z_beta = _z_for_power(power)
    p_bar = (p0 + p1) / 2
    q_bar = 1 - p_bar
    q0 = 1 - p0
    q1 = 1 - p1

    numerator = (
        z_alpha * math.sqrt(2 * p_bar * q_bar)
        + z_beta * math.sqrt(p0 * q0 + p1 * q1)
    ) ** 2
    denom = (p0 - p1) ** 2
    n = math.ceil(numerator / denom)

    note = ""
    if min(p0, p1, 1 - p0, 1 - p1) < 0.05:
        note = (
            "near-boundary proportion (<5%); normal approximation may under-estimate. "
            "Recommend running Fisher's exact at analysis time and considering N += 25%."
        )
    return PowerResult(n_per_arm=n, method="normal-approx", note=note)


# --------------------------------------------------------------------------- #
# Inverse-CDF helpers (avoid scipy)                                           #
# --------------------------------------------------------------------------- #


def _ndtri(p: float) -> float:
    """Approximate inverse of the standard normal CDF (probit function).

    Uses the Beasley-Springer-Moro algorithm; accuracy ~1e-9 in the body of
    the distribution, which is plenty for sample-size calculations.
    """
    if not (0.0 < p < 1.0):
        raise ValueError("p must be in (0, 1)")

    # Coefficients for rational approximation.
    a = [
        -3.969683028665376e+01,  2.209460984245205e+02,
        -2.759285104469687e+02,  1.383577518672690e+02,
        -3.066479806614716e+01,  2.506628277459239e+00,
    ]
    b = [
        -5.447609879822406e+01,  1.615858368580409e+02,
        -1.556989798598866e+02,  6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00,  2.938163982698783e+00,
    ]
    d = [
         7.784695709041462e-03,  3.224671290700398e-01,
         2.445134137142996e+00,  3.754408661907416e+00,
    ]
    plow = 0.02425
    phigh = 1 - plow

    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        num = (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5])
        den = ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
        return num / den

    if p <= phigh:
        q = p - 0.5
        r = q * q
        num = (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q
        den = (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)
        return num / den

    q = math.sqrt(-2 * math.log(1 - p))
    num = -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5])
    den = ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    return num / den


def _z_for_two_sided_alpha(alpha: float) -> float:
    return _ndtri(1 - alpha / 2)


def _z_for_power(power: float) -> float:
    return _ndtri(power)
