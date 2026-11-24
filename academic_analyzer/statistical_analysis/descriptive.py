"""
descriptive.py – Descriptive statistics engine for the Academic Analyzer.

All functions operate on real data arrays; nothing is hard-coded.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Core descriptive stats
# ---------------------------------------------------------------------------

def calculate_descriptive_stats(marks: list[float]) -> dict:
    """
    Given a list of numeric marks, return a comprehensive stats dictionary.

    Keys
    ----
    count, mean, median, mode,
    min_val, max_val, range_val,
    variance (population), std_dev (population),
    sample_variance, sample_std_dev,
    skewness, kurtosis,
    p25, p75, iqr,
    coefficient_of_variation,
    outliers_iqr, outliers_zscore
    """
    empty_result = {
        "count": 0,
        "mean": None, "median": None, "mode": None,
        "min_val": None, "max_val": None, "range_val": None,
        "variance": None, "std_dev": None,
        "sample_variance": None, "sample_std_dev": None,
        "skewness": None, "kurtosis": None,
        "p25": None, "p75": None, "iqr": None,
        "coefficient_of_variation": None,
        "outliers_iqr": [], "outliers_zscore": [],
    }

    if not marks:
        return empty_result

    arr = np.array([m for m in marks if m is not None], dtype=float)
    n = len(arr)

    if n == 0:
        return empty_result

    result: dict = {"count": int(n)}

    result["mean"] = float(np.mean(arr))
    result["median"] = float(np.median(arr))

    # Mode – handle multimodal
    mode_result = stats.mode(arr, keepdims=True)
    mode_vals = mode_result.mode
    mode_counts = mode_result.count
    # If every value appears exactly once, report all; else find max frequency
    max_count = int(np.max(mode_counts)) if len(mode_counts) > 0 else 1
    if max_count == 1 and n > 1:
        result["mode"] = "No mode (all values unique)"
    else:
        # Find all values with max frequency
        unique_vals, val_counts = np.unique(arr, return_counts=True)
        modal_vals = unique_vals[val_counts == max_count]
        result["mode"] = float(modal_vals[0]) if len(modal_vals) == 1 else [float(v) for v in modal_vals]

    result["min_val"] = float(np.min(arr))
    result["max_val"] = float(np.max(arr))
    result["range_val"] = float(result["max_val"] - result["min_val"])

    # Population variance & std
    result["variance"] = float(np.var(arr, ddof=0))
    result["std_dev"] = float(np.std(arr, ddof=0))

    # Sample variance & std (require n >= 2)
    if n >= 2:
        result["sample_variance"] = float(np.var(arr, ddof=1))
        result["sample_std_dev"] = float(np.std(arr, ddof=1))
        result["skewness"] = float(stats.skew(arr))
        result["kurtosis"] = float(stats.kurtosis(arr))  # excess kurtosis
    else:
        result["sample_variance"] = None
        result["sample_std_dev"] = None
        result["skewness"] = None
        result["kurtosis"] = None

    # Percentiles & IQR
    result["p25"] = float(np.percentile(arr, 25))
    result["p75"] = float(np.percentile(arr, 75))
    result["iqr"] = float(result["p75"] - result["p25"])

    # Coefficient of variation (%)
    if result["mean"] and abs(result["mean"]) > 1e-9:
        result["coefficient_of_variation"] = float(result["std_dev"] / abs(result["mean"]) * 100)
    else:
        result["coefficient_of_variation"] = None

    result["outliers_iqr"] = detect_outliers_iqr(marks)
    result["outliers_zscore"] = detect_outliers_zscore(marks)

    return result


# ---------------------------------------------------------------------------
# Frequency distribution
# ---------------------------------------------------------------------------

def calculate_frequency_distribution(marks: list[float], bins: int = 10) -> dict:
    """
    Returns a dict with:
      bin_edges       – list of floats (len = bins + 1)
      bin_labels      – list of string labels for each bin
      frequencies     – list of int counts per bin
      relative_frequencies – list of float proportions (sum ≈ 1.0)
      cumulative_frequencies – list of int cumulative counts
    """
    if not marks:
        return {
            "bin_edges": [], "bin_labels": [],
            "frequencies": [], "relative_frequencies": [],
            "cumulative_frequencies": [],
        }

    arr = np.array([m for m in marks if m is not None], dtype=float)
    if len(arr) == 0:
        return {
            "bin_edges": [], "bin_labels": [],
            "frequencies": [], "relative_frequencies": [],
            "cumulative_frequencies": [],
        }

    freqs, edges = np.histogram(arr, bins=bins)
    n = len(arr)
    relative = freqs / n
    cumulative = np.cumsum(freqs)

    labels = [
        f"{edges[i]:.2f} – {edges[i+1]:.2f}"
        for i in range(len(edges) - 1)
    ]

    return {
        "bin_edges": [float(e) for e in edges],
        "bin_labels": labels,
        "frequencies": [int(f) for f in freqs],
        "relative_frequencies": [float(r) for r in relative],
        "cumulative_frequencies": [int(c) for c in cumulative],
    }


# ---------------------------------------------------------------------------
# Subject comparison
# ---------------------------------------------------------------------------

def calculate_subject_comparison(subject_stats_list: list[dict]) -> list[dict]:
    """
    Given a list of dicts – each must have at minimum:
        {"subject_name": str, "mean": float, ...}
    Returns the list sorted descending by mean.

    Each dict gets an extra "rank" key (1 = highest mean).
    """
    valid = [s for s in subject_stats_list if s.get("mean") is not None]
    ranked = sorted(valid, key=lambda s: s["mean"], reverse=True)
    for i, s in enumerate(ranked, start=1):
        s["rank"] = i
    return ranked


# ---------------------------------------------------------------------------
# Class performance summary (across all subjects / all marks)
# ---------------------------------------------------------------------------

def get_class_performance_summary(all_marks: list[float]) -> dict:
    """
    Returns overall descriptive stats for the entire class (all subjects combined).
    Adds performance band counts:
        pass (>=40), distinction (>=75), fail (<40)
    """
    base = calculate_descriptive_stats(all_marks)
    arr = np.array([m for m in all_marks if m is not None], dtype=float)

    if len(arr) == 0:
        base.update({
            "total_students": 0,
            "pass_count": 0,
            "fail_count": 0,
            "distinction_count": 0,
            "pass_rate_pct": None,
        })
        return base

    base["total_students"] = int(len(arr))
    base["pass_count"] = int(np.sum(arr >= 40))
    base["fail_count"] = int(np.sum(arr < 40))
    base["distinction_count"] = int(np.sum(arr >= 75))
    base["pass_rate_pct"] = float(base["pass_count"] / len(arr) * 100)

    return base


# ---------------------------------------------------------------------------
# Outlier detection
# ---------------------------------------------------------------------------

def detect_outliers_iqr(marks: list[float]) -> list[float]:
    """
    Returns the list of values that lie outside [Q1 - 1.5×IQR, Q3 + 1.5×IQR].
    """
    if not marks or len(marks) < 4:
        return []

    arr = np.array([m for m in marks if m is not None], dtype=float)
    if len(arr) < 4:
        return []

    q1 = np.percentile(arr, 25)
    q3 = np.percentile(arr, 75)
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr

    outliers = arr[(arr < lower_fence) | (arr > upper_fence)]
    return [float(o) for o in sorted(outliers)]


def detect_outliers_zscore(marks: list[float], threshold: float = 2.5) -> list[float]:
    """
    Returns the list of values whose |z-score| exceeds *threshold* (default 2.5).
    """
    if not marks or len(marks) < 2:
        return []

    arr = np.array([m for m in marks if m is not None], dtype=float)
    if len(arr) < 2:
        return []

    mu = np.mean(arr)
    sigma = np.std(arr, ddof=1)

    if sigma < 1e-9:
        return []

    z_scores = np.abs((arr - mu) / sigma)
    outliers = arr[z_scores > threshold]
    return [float(o) for o in sorted(outliers)]
