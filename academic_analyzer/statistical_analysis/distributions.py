"""
distributions.py – Probability distribution fitting and analysis.

Supports:
  • Normality testing (Shapiro-Wilk / D'Agostino-Pearson)
  • Normal distribution fitting via MLE
  • Binomial pass/fail modelling
  • Z-scores, percentile ranks, and probability ranges
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# Normality testing
# ---------------------------------------------------------------------------

def test_normality(marks: list[float]) -> dict:
    """
    Run an appropriate normality test:
      - Shapiro-Wilk  when n < 50
      - D'Agostino-Pearson (normaltest) when n >= 50

    Returns
    -------
    dict with keys:
        test_name, statistic, p_value, is_normal, confidence, interpretation
    """
    arr = np.array([m for m in marks if m is not None], dtype=float)
    n = len(arr)

    if n < 3:
        return {
            "test_name": "N/A",
            "statistic": None,
            "p_value": None,
            "is_normal": None,
            "confidence": "N/A",
            "interpretation": "Insufficient data (need at least 3 observations) to test normality.",
        }

    alpha = 0.05

    if n < 50:
        stat, p_value = stats.shapiro(arr)
        test_name = "Shapiro-Wilk"
    else:
        stat, p_value = stats.normaltest(arr)
        test_name = "D'Agostino-Pearson"

    is_normal = bool(p_value > alpha)

    if is_normal:
        interpretation = (
            f"The {test_name} test yielded a p-value of {p_value:.4f} (> 0.05), "
            f"so we fail to reject the null hypothesis. The marks for this subject "
            f"appear to follow a normal distribution at the 95% confidence level. "
            f"Statistical methods that assume normality are appropriate."
        )
    else:
        interpretation = (
            f"The {test_name} test yielded a p-value of {p_value:.4f} (≤ 0.05), "
            f"so the null hypothesis of normality is rejected at the 95% confidence level. "
            f"The marks do NOT appear to follow a normal distribution. "
            f"Non-parametric alternatives (e.g., Mann-Whitney U) may be preferable."
        )

    return {
        "test_name": test_name,
        "statistic": float(stat),
        "p_value": float(p_value),
        "is_normal": is_normal,
        "confidence": "95%",
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# Normal distribution fitting
# ---------------------------------------------------------------------------

def fit_normal_distribution(marks: list[float]) -> dict:
    """
    Fit a normal distribution to *marks* using maximum-likelihood estimation.

    Returns
    -------
    dict with:
        mean, std,
        pdf_x  – 200-point x-grid spanning [min-3σ, max+3σ]
        pdf_y  – corresponding PDF values
        cdf_values – CDF evaluated at each mark (sorted)
        fit_quality – KS test statistic (lower ≈ better fit)
    """
    arr = np.array([m for m in marks if m is not None], dtype=float)

    if len(arr) < 2:
        return {
            "mean": None, "std": None,
            "pdf_x": [], "pdf_y": [],
            "cdf_values": [],
            "fit_quality": None,
        }

    mu, sigma = float(np.mean(arr)), float(np.std(arr, ddof=1))

    if sigma < 1e-9:
        sigma = 1e-9  # guard against degenerate distributions

    # 200-point grid for smooth curve
    x_min = mu - 4 * sigma
    x_max = mu + 4 * sigma
    pdf_x = np.linspace(x_min, x_max, 200)
    pdf_y = stats.norm.pdf(pdf_x, loc=mu, scale=sigma)

    # CDF at each sorted mark
    sorted_marks = np.sort(arr)
    cdf_values = stats.norm.cdf(sorted_marks, loc=mu, scale=sigma)

    # Kolmogorov-Smirnov goodness-of-fit
    ks_stat, _ = stats.kstest(arr, "norm", args=(mu, sigma))

    return {
        "mean": mu,
        "std": sigma,
        "pdf_x": [float(v) for v in pdf_x],
        "pdf_y": [float(v) for v in pdf_y],
        "cdf_values": [float(v) for v in cdf_values],
        "fit_quality": float(ks_stat),
    }


# ---------------------------------------------------------------------------
# Binomial pass/fail model
# ---------------------------------------------------------------------------

def binomial_pass_fail(
    marks: list[float],
    pass_threshold: float = 40.0,
    max_marks: float = 100.0,
) -> dict:
    """
    Model pass/fail outcomes as Binomial(n, p).

    Parameters
    ----------
    marks          : list of student marks
    pass_threshold : minimum marks to be considered a pass
    max_marks      : maximum possible marks (for context only)

    Returns
    -------
    dict with:
        n, p_empirical, expected_passes, binomial_variance, binomial_std,
        p_majority_pass,       # P(X > n/2)
        pmf_k, pmf_prob,       # capped at min(n, 20) k-values
        pass_count, fail_count,
        pass_rate_pct,
        assumptions, interpretation
    """
    arr = np.array([m for m in marks if m is not None], dtype=float)
    n = int(len(arr))

    if n == 0:
        return {
            "n": 0, "p_empirical": None, "expected_passes": None,
            "binomial_variance": None, "binomial_std": None,
            "p_majority_pass": None,
            "pmf_k": [], "pmf_prob": [],
            "pass_count": 0, "fail_count": 0, "pass_rate_pct": None,
            "assumptions": "No data provided.",
            "interpretation": "No marks available for binomial analysis.",
        }

    pass_count = int(np.sum(arr >= pass_threshold))
    fail_count = n - pass_count
    p = pass_count / n  # empirical probability of passing

    # Binomial moments
    expected = n * p
    variance = n * p * (1 - p)
    std_binom = math.sqrt(variance)

    # P(X > n/2) = probability that more than half the class passes
    # Using survival function of binomial
    half = n / 2
    p_majority = float(stats.binom.sf(half, n, p))  # P(X > n/2)

    # PMF – display up to min(n, 20) values to keep the payload manageable
    k_max = min(n, 20)
    k_vals = list(range(0, k_max + 1))
    pmf_probs = [float(stats.binom.pmf(k, n, p)) for k in k_vals]

    assumptions = (
        f"Each student's outcome (pass/fail) is treated as an independent Bernoulli trial "
        f"with empirical probability p = {p:.4f} (estimated from the class data). "
        f"The total number of trials n = {n} (class size). "
        f"Pass threshold = {pass_threshold} out of {max_marks} marks."
    )

    interpretation = (
        f"Out of {n} students, {pass_count} passed ({p*100:.1f}%). "
        f"Under the Binomial model, the expected number of passes is {expected:.1f} "
        f"(± {std_binom:.2f} students, 1 SD). "
        f"The probability that more than half the class passes is {p_majority*100:.1f}%."
    )

    return {
        "n": n,
        "p_empirical": float(p),
        "empirical_p": float(p),
        "expected_passes": float(expected),
        "binomial_variance": float(variance),
        "binomial_std": float(std_binom),
        "p_majority_pass": p_majority,
        "pmf_k": k_vals,
        "pmf_prob": pmf_probs,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate_pct": float(p * 100),
        "assumptions": assumptions,
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# Z-scores
# ---------------------------------------------------------------------------

def calculate_z_scores(marks: list[float]) -> list[float]:
    """Return the z-score for every mark in *marks* (population std)."""
    arr = np.array([m for m in marks if m is not None], dtype=float)

    if len(arr) < 2:
        return [0.0] * len(arr)

    mu = np.mean(arr)
    sigma = np.std(arr, ddof=0)

    if sigma < 1e-9:
        return [0.0] * len(arr)

    return [float((m - mu) / sigma) for m in arr]


# ---------------------------------------------------------------------------
# Percentile rank
# ---------------------------------------------------------------------------

def get_percentile_rank(marks: list[float], target_mark: float) -> float:
    """
    Percentile rank of *target_mark* within *marks*.

    Uses: percentile_rank = (number of marks below target / n) × 100
    """
    arr = np.array([m for m in marks if m is not None], dtype=float)
    n = len(arr)
    if n == 0:
        return 0.0
    below = np.sum(arr < target_mark)
    return float(below / n * 100)


# ---------------------------------------------------------------------------
# Probability that a random student falls in [lower, upper]
# ---------------------------------------------------------------------------

def calculate_probability_range(
    marks: list[float], lower: float, upper: float
) -> float:
    """
    Probability that a randomly selected student's mark falls in [lower, upper],
    computed from the fitted normal distribution.

    Returns a value in [0, 1].
    """
    arr = np.array([m for m in marks if m is not None], dtype=float)

    if len(arr) < 2:
        return 0.0

    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))

    if sigma < 1e-9:
        # Degenerate: all marks equal
        return 1.0 if lower <= mu <= upper else 0.0

    prob = stats.norm.cdf(upper, loc=mu, scale=sigma) - stats.norm.cdf(lower, loc=mu, scale=sigma)
    return float(np.clip(prob, 0.0, 1.0))
