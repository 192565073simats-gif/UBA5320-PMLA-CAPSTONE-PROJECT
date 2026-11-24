"""
statistical_analysis/interpretation.py — Human-readable interpretation helpers.
"""

from typing import Any, Dict, List, Optional, Tuple


def categorize_student(
    average_mark: float,
    max_mark: float = 100.0,
    mean: Optional[float] = None,
    std_dev: Optional[float] = None,
    thresholds: Optional[dict] = None,
) -> str:
    """
    Map a student's mark/average to a performance category.

    If mean and std_dev are provided, categorization is based on z-scores:
        z ≥ 1.0  → Excellent
        0.0 ≤ z < 1.0 → Good
        -1.0 ≤ z < 0.0 → Average
        z < -1.0 → Below Average

    Otherwise, thresholds (% of max_mark):
        ≥ 75% → Excellent
        ≥ 60% → Good
        ≥ 40% → Average
        <  40% → Below Average
    """
    if mean is not None and std_dev is not None and std_dev > 0:
        z = (average_mark - mean) / std_dev
        if z >= 1.0:
            return "Excellent"
        elif z >= 0.0:
            return "Good"
        elif z >= -1.0:
            return "Average"
        else:
            return "Below Average"

    pct = (average_mark / max_mark) * 100 if max_mark else 0
    if pct >= 75:
        return "Excellent"
    if pct >= 60:
        return "Good"
    if pct >= 40:
        return "Average"
    return "Below Average"


def identify_at_risk_students(
    student_scores: List[Dict[str, Any]],
    z_threshold: float = -1.5,
    pass_mark: float = 40.0,
    mean: Optional[float] = None,
    std_dev: Optional[float] = None,
    threshold_z: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Identify at-risk students from a list of student score dicts.

    A student is flagged as at-risk when their z-score < z_threshold
    OR their mark is below pass_mark.
    """
    tz = threshold_z if threshold_z is not None else z_threshold
    at_risk = []
    for entry in student_scores:
        reasons: List[str] = []
        z = entry.get("z_score")
        mark = entry.get("marks", entry.get("average_marks", 0))

        if z is None and mean is not None and std_dev is not None and std_dev > 0:
            z = (mark - mean) / std_dev

        if z is not None and z < tz:
            reasons.append(f"z-score {z:.2f} (well below class mean)")
        elif mark < pass_mark:
            reasons.append(f"mark {mark:.1f} below pass mark ({pass_mark})")

        if reasons:
            at_risk.append({**entry, "z_score": z, "at_risk": True, "risk_reasons": reasons})

    return at_risk


def interpret_descriptive_stats(stats: Dict[str, Any]) -> str:
    """
    Generate a plain-English interpretation of descriptive statistics.

    Args:
        stats: dict returned by calculate_descriptive_stats.

    Returns:
        Multi-sentence interpretation string.
    """
    if stats.get("count", 0) == 0:
        return "No data available for interpretation."

    mean = stats.get("mean", 0)
    std = stats.get("std_dev", 0)
    skewness = stats.get("skewness")
    kurtosis = stats.get("kurtosis")

    sentences: List[str] = []

    # Central tendency
    sentences.append(
        f"The class has a mean score of {mean:.1f} with a standard deviation of {std:.1f}."
    )

    # Variability
    if std < 10:
        sentences.append("Score variability is low, indicating a homogeneous class.")
    elif std < 20:
        sentences.append("Score variability is moderate.")
    else:
        sentences.append("High variability suggests a wide range of student performance.")

    # Skewness
    if skewness is not None:
        if skewness > 0.5:
            sentences.append(
                "The distribution is positively skewed, meaning most students scored below the mean."
            )
        elif skewness < -0.5:
            sentences.append(
                "The distribution is negatively skewed, meaning most students scored above the mean."
            )
        else:
            sentences.append("The distribution is approximately symmetric.")

    # Kurtosis
    if kurtosis is not None:
        if kurtosis > 1:
            sentences.append(
                "High kurtosis indicates heavy tails — a few outlier scores are present."
            )
        elif kurtosis < -1:
            sentences.append(
                "Low kurtosis indicates light tails — scores are clustered closely around the mean."
            )

    return " ".join(sentences)


def suggest_support(category: str, z_score: Optional[float] = None) -> List[str]:
    """
    Return non-judgmental support suggestions for a student based on their category.

    These are intended for teacher review, not direct student communication.
    """
    suggestions: Dict[str, List[str]] = {
        "Excellent": [
            "Consider providing enrichment activities or advanced-level challenges.",
            "Peer-tutoring opportunities may be beneficial.",
        ],
        "Good": [
            "Encourage continued engagement with the subject matter.",
            "Identify specific topics for consolidation if any marks dipped.",
        ],
        "Average": [
            "Review foundational concepts that may require reinforcement.",
            "One-on-one check-ins could help identify any learning gaps.",
            "Encourage active participation in class discussions.",
        ],
        "Below Average": [
            "Recommend additional academic support sessions.",
            "Collaborate with the student to set achievable short-term goals.",
            "Consider a referral to the academic support centre.",
            "Review attendance and engagement records for additional context.",
        ],
    }
    base = suggestions.get(category, ["Continue monitoring student progress."])
    if z_score is not None and z_score < -2.0:
        base.append(
            "Student's score is significantly below the class average — priority review recommended."
        )
    return base
