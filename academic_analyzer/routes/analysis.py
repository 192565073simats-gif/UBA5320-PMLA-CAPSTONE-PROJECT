"""
routes/analysis.py — Statistical analysis endpoints.
"""

from typing import List, Optional

import numpy as np
import scipy.stats as stats
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from academic_analyzer.auth import get_current_user
from academic_analyzer.database import get_db
from academic_analyzer.models import Assessment, Subject
from academic_analyzer.schemas import AnalysisResult, StatsSummary

router = APIRouter()


def _compute_stats(marks: List[float]) -> StatsSummary:
    """Compute descriptive statistics for a list of mark values."""
    if not marks:
        return StatsSummary()

    arr = np.array(marks, dtype=float)
    n = len(arr)
    mean = float(np.mean(arr))
    median = float(np.median(arr))
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))
    range_val = max_val - min_val
    variance = float(np.var(arr, ddof=1)) if n > 1 else 0.0
    std_dev = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    skewness = float(stats.skew(arr)) if n >= 3 else None
    kurt = float(stats.kurtosis(arr)) if n >= 4 else None

    # Mode: most frequent value (use scipy for robustness)
    mode_result = stats.mode(arr, keepdims=True)
    mode_val = float(mode_result.mode[0]) if n > 0 else None

    return StatsSummary(
        mean=mean,
        median=median,
        mode=mode_val,
        min_val=min_val,
        max_val=max_val,
        range_val=range_val,
        variance=variance,
        std_dev=std_dev,
        count=float(n),
        skewness=skewness,
        kurtosis=kurt,
    )


def _fit_normal(marks: List[float]) -> dict:
    """Fit a normal distribution and return mu, sigma, and goodness-of-fit p-value."""
    if len(marks) < 3:
        return {"mu": None, "sigma": None, "p_value": None, "fits_normal": False}
    arr = np.array(marks, dtype=float)
    mu, sigma = stats.norm.fit(arr)
    _, p_value = stats.normaltest(arr)
    return {
        "mu": round(float(mu), 4),
        "sigma": round(float(sigma), 4),
        "p_value": round(float(p_value), 4),
        "fits_normal": bool(p_value >= 0.05),
    }


def _interpret(stats_summary: StatsSummary, normal_fit: dict) -> tuple[str, str]:
    """Return (distribution_type, interpretation) based on computed stats."""
    if stats_summary.count is None or stats_summary.count == 0:
        return "unknown", "No data available for analysis."

    skew = stats_summary.skewness or 0.0
    kurt = stats_summary.kurtosis or 0.0
    fits = normal_fit.get("fits_normal", False)

    if fits:
        dist_type = "Normal"
        interp = (
            f"The marks follow a Normal distribution (μ={normal_fit['mu']}, "
            f"σ={normal_fit['sigma']}). Performance is evenly distributed around the mean."
        )
    elif skew > 0.5:
        dist_type = "Positively Skewed"
        interp = (
            "Marks are positively skewed — most students scored below the mean, "
            "with a tail of high achievers."
        )
    elif skew < -0.5:
        dist_type = "Negatively Skewed"
        interp = (
            "Marks are negatively skewed — most students scored above the mean, "
            "with a tail of low achievers."
        )
    elif kurt > 1:
        dist_type = "Leptokurtic"
        interp = (
            "Marks show a leptokurtic distribution (heavy tails / sharp peak), "
            "indicating clustering around the mean with some outliers."
        )
    elif kurt < -1:
        dist_type = "Platykurtic"
        interp = (
            "Marks show a platykurtic distribution (light tails / flat peak), "
            "indicating a wide spread with few extreme values."
        )
    else:
        dist_type = "Approximately Normal"
        interp = "Marks approximate a Normal distribution but do not pass the formal normality test."

    return dist_type, interp


@router.get("/subject/{subject_id}", response_model=AnalysisResult)
def analyse_subject(
    subject_id: int,
    assessment_type: Optional[str] = Query(None, description="Filter by 'internal' or 'exam'"),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Full statistical analysis for a subject."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    q = (
        db.query(Assessment)
        .filter(Assessment.subject_id == subject_id, Assessment.is_missing == False)  # noqa: E712
    )
    if assessment_type:
        q = q.filter(Assessment.assessment_type == assessment_type)

    assessments = q.all()
    marks = [a.marks for a in assessments if a.marks is not None]

    if not marks:
        raise HTTPException(
            status_code=422,
            detail="No marks data found for this subject with the given filters.",
        )

    stats_summary = _compute_stats(marks)
    normal_fit = _fit_normal(marks)
    dist_type, interp = _interpret(stats_summary, normal_fit)

    return AnalysisResult(
        subject_id=subject.id,
        subject_name=subject.subject_name,
        stats=stats_summary,
        normal_fit=normal_fit,
        distribution_type=dist_type,
        interpretation=interp,
    )


@router.get("/department/{department}", response_model=List[AnalysisResult])
def analyse_department(
    department: str,
    assessment_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Analyse all subjects in a department."""
    subjects = db.query(Subject).filter(Subject.department == department).all()
    if not subjects:
        raise HTTPException(status_code=404, detail=f"No subjects found for department '{department}'")

    results = []
    for subject in subjects:
        q = db.query(Assessment).filter(
            Assessment.subject_id == subject.id,
            Assessment.is_missing == False,  # noqa: E712
        )
        if assessment_type:
            q = q.filter(Assessment.assessment_type == assessment_type)
        marks = [a.marks for a in q.all() if a.marks is not None]
        if not marks:
            continue
        stats_summary = _compute_stats(marks)
        normal_fit = _fit_normal(marks)
        dist_type, interp = _interpret(stats_summary, normal_fit)
        results.append(
            AnalysisResult(
                subject_id=subject.id,
                subject_name=subject.subject_name,
                stats=stats_summary,
                normal_fit=normal_fit,
                distribution_type=dist_type,
                interpretation=interp,
            )
        )
    return results


@router.get("/student/{student_id}")
def analyse_student(
    student_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return per-subject performance summary for a single student."""
    from academic_analyzer.models import Student  # noqa: PLC0415

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    assessments = (
        db.query(Assessment)
        .filter(Assessment.student_id == student_id, Assessment.is_missing == False)  # noqa: E712
        .all()
    )

    subject_marks: dict[int, dict] = {}
    for a in assessments:
        if a.marks is None:
            continue
        if a.subject_id not in subject_marks:
            subject_marks[a.subject_id] = {
                "subject_id": a.subject_id,
                "subject_name": a.subject.subject_name if a.subject else str(a.subject_id),
                "marks": [],
            }
        subject_marks[a.subject_id]["marks"].append(a.marks)

    return {
        "student_id": student.student_id,
        "name": student.name,
        "subjects": [
            {
                "subject_id": v["subject_id"],
                "subject_name": v["subject_name"],
                "marks": v["marks"],
                "average": round(sum(v["marks"]) / len(v["marks"]), 2) if v["marks"] else None,
            }
            for v in subject_marks.values()
        ],
    }


@router.get("/distribution/{subject_id}")
def analyse_distribution(
    subject_id: int,
    assessment_type: Optional[str] = Query(None),
    pass_threshold: float = Query(40.0),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Full probability distribution analysis (Normal & Binomial)."""
    from academic_analyzer.statistical_analysis.distributions import (
        test_normality,
        fit_normal_distribution,
        binomial_pass_fail,
    )

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    q = db.query(Assessment).filter(
        Assessment.subject_id == subject_id,
        Assessment.is_missing == False,
    )
    if assessment_type:
        q = q.filter(Assessment.assessment_type == assessment_type)

    marks = [a.marks for a in q.all() if a.marks is not None]
    if not marks:
        raise HTTPException(status_code=422, detail="No marks data found for this subject.")

    norm_test = test_normality(marks)
    norm_fit = fit_normal_distribution(marks)
    binom = binomial_pass_fail(marks, pass_threshold=pass_threshold, max_marks=subject.max_marks)

    # Compute z-scores for students
    mean_val = float(np.mean(marks))
    std_val = float(np.std(marks, ddof=1)) if len(marks) > 1 else 0.0

    assessments = q.all()
    student_zscores = []
    for a in assessments:
        if a.marks is not None:
            z = round((a.marks - mean_val) / std_val, 2) if std_val > 0 else 0.0
            student_zscores.append({
                "student_id": a.student.student_id if a.student else str(a.student_id),
                "name": a.student.name if a.student else "Unknown",
                "marks": a.marks,
                "z_score": z,
            })

    return {
        "subject_id": subject.id,
        "subject_name": subject.subject_name,
        "marks_count": len(marks),
        "normality_test": norm_test,
        "normal_fit": norm_fit,
        "binomial_analysis": binom,
        "student_zscores": student_zscores,
    }
