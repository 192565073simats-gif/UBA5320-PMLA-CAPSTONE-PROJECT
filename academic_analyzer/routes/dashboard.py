"""
routes/dashboard.py — Dashboard summary and statistics endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from academic_analyzer.auth import get_current_user
from academic_analyzer.database import get_db
from academic_analyzer.models import Assessment, Student, Subject, AnalysisReport

router = APIRouter()


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """High-level counts for the dashboard home page."""
    total_students = db.query(func.count(Student.id)).scalar()
    total_subjects = db.query(func.count(Subject.id)).scalar()
    total_assessments = db.query(func.count(Assessment.id)).scalar()
    missing_marks = (
        db.query(func.count(Assessment.id))
        .filter(Assessment.is_missing == True)  # noqa: E712
        .scalar()
    )
    total_reports = db.query(func.count(AnalysisReport.id)).scalar()

    # Department breakdown
    dept_counts = (
        db.query(Student.department, func.count(Student.id))
        .group_by(Student.department)
        .all()
    )

    # Average marks per subject (top 5)
    avg_marks_per_subject = (
        db.query(
            Subject.subject_name,
            func.avg(Assessment.marks).label("avg_marks"),
        )
        .join(Assessment, Assessment.subject_id == Subject.id)
        .filter(Assessment.is_missing == False)  # noqa: E712
        .group_by(Subject.subject_name)
        .order_by(func.avg(Assessment.marks).desc())
        .limit(5)
        .all()
    )

    return {
        "total_students": total_students,
        "total_subjects": total_subjects,
        "total_assessments": total_assessments,
        "missing_marks": missing_marks,
        "total_reports": total_reports,
        "departments": [
            {"department": dept, "count": cnt} for dept, cnt in dept_counts
        ],
        "top_subjects_by_avg": [
            {"subject": name, "avg_marks": round(avg or 0.0, 2)}
            for name, avg in avg_marks_per_subject
        ],
    }
