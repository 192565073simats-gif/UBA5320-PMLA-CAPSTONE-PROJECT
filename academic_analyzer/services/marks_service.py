"""
Marks / Assessment Service — CRUD + bulk-import operations.
"""
import os
from typing import Dict, List, Optional

import pandas as pd
from fastapi import HTTPException
from sqlalchemy.orm import Session

from academic_analyzer.models import Assessment, Student, Subject
from academic_analyzer.schemas import AssessmentCreate, AssessmentUpdate


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def get_marks_for_subject(db: Session, subject_id: int) -> List[Assessment]:
    """Return all non-missing assessments for a subject."""
    return (
        db.query(Assessment)
        .filter(Assessment.subject_id == subject_id, Assessment.is_missing == False)
        .all()
    )


def get_marks_for_student(db: Session, student_id: int) -> List[Assessment]:
    """Return all assessments (including missing) for a student."""
    return (
        db.query(Assessment)
        .filter(Assessment.student_id == student_id)
        .all()
    )


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def _check_duplicate(
    db: Session,
    student_id: int,
    subject_id: int,
    assessment_type: str,
    exclude_id: Optional[int] = None,
) -> None:
    """Raise HTTP 400 if a duplicate (student, subject, type) row already exists."""
    q = db.query(Assessment).filter(
        Assessment.student_id == student_id,
        Assessment.subject_id == subject_id,
        Assessment.assessment_type == assessment_type,
    )
    if exclude_id is not None:
        q = q.filter(Assessment.id != exclude_id)
    if q.first():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Assessment record for student_id={student_id}, "
                f"subject_id={subject_id}, type='{assessment_type}' already exists."
            ),
        )


def add_assessment(db: Session, data: AssessmentCreate) -> Assessment:
    """Create a new Assessment.

    - Validates marks within the subject's min/max range.
    - Sets is_missing=True when marks is None.
    - Prevents duplicate (student_id, subject_id, assessment_type).
    """
    # Verify student & subject exist
    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student id={data.student_id} not found.")

    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail=f"Subject id={data.subject_id} not found.")

    # Duplicate check
    _check_duplicate(db, data.student_id, data.subject_id, data.assessment_type)

    is_missing = data.marks is None
    marks = data.marks

    # Range validation
    if marks is not None:
        if marks < subject.min_marks or marks > subject.max_marks:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Marks {marks} out of range [{subject.min_marks}, {subject.max_marks}] "
                    f"for subject '{subject.subject_name}'."
                ),
            )

    assessment = Assessment(
        student_id=data.student_id,
        subject_id=data.subject_id,
        assessment_type=data.assessment_type,
        marks=marks,
        is_missing=is_missing,
        remarks=data.remarks,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def update_assessment(
    db: Session, assessment_id: int, data: AssessmentUpdate
) -> Assessment:
    """Update an Assessment.  Raises HTTP 404 if not found."""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    update_data = data.model_dump(exclude_unset=True)

    # If marks is being updated, re-validate range
    new_marks = update_data.get("marks", assessment.marks)
    if new_marks is not None:
        subject = db.query(Subject).filter(Subject.id == assessment.subject_id).first()
        if subject and (new_marks < subject.min_marks or new_marks > subject.max_marks):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Marks {new_marks} out of range [{subject.min_marks}, {subject.max_marks}]."
                ),
            )

    # If assessment_type changes, re-check duplicate
    if "assessment_type" in update_data:
        _check_duplicate(
            db,
            assessment.student_id,
            assessment.subject_id,
            update_data["assessment_type"],
            exclude_id=assessment_id,
        )

    for field, value in update_data.items():
        setattr(assessment, field, value)

    # Sync is_missing with marks
    if "marks" in update_data:
        assessment.is_missing = update_data["marks"] is None

    db.commit()
    db.refresh(assessment)
    return assessment


def delete_assessment(db: Session, assessment_id: int) -> bool:
    """Delete an Assessment.  Returns True on success, raises 404 if not found."""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    db.delete(assessment)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Bulk import
# ---------------------------------------------------------------------------

def bulk_import_from_csv(db: Session, file_path: str) -> Dict:
    """Import assessments from a CSV file.

    Expected columns: student_id, subject_code, assessment_type, marks (optional)

    Returns a dict: {success_count, error_count, errors: [{row, message}]}
    """
    REQUIRED_COLS = {"student_id", "subject_code", "assessment_type"}

    errors: List[Dict] = []
    success_count = 0
    error_count = 0

    try:
        df = pd.read_csv(file_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {exc}")

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    missing_cols = REQUIRED_COLS - set(df.columns)
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns: {missing_cols}",
        )

    has_marks_col = "marks" in df.columns

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 1-indexed, header is row 1
        try:
            sid_code = str(row["student_id"]).strip()
            subject_code = str(row["subject_code"]).strip()
            assessment_type = str(row["assessment_type"]).strip().lower()

            if not sid_code or not subject_code or not assessment_type:
                raise ValueError("student_id, subject_code, and assessment_type must not be empty.")

            # Lookup student
            student = (
                db.query(Student).filter(Student.student_id == sid_code).first()
            )
            if not student:
                raise ValueError(f"Student with student_id='{sid_code}' not found.")

            # Lookup subject
            subject = (
                db.query(Subject).filter(Subject.subject_code == subject_code).first()
            )
            if not subject:
                raise ValueError(f"Subject with subject_code='{subject_code}' not found.")

            # Parse marks
            marks: Optional[float] = None
            if has_marks_col:
                raw_marks = row["marks"]
                if pd.notna(raw_marks) and str(raw_marks).strip() != "":
                    try:
                        marks = float(raw_marks)
                    except ValueError:
                        raise ValueError(f"Invalid marks value: '{raw_marks}'.")

            is_missing = marks is None

            if marks is not None:
                if marks < subject.min_marks or marks > subject.max_marks:
                    raise ValueError(
                        f"Marks {marks} out of range [{subject.min_marks}, {subject.max_marks}]."
                    )

            # Duplicate check (skip rather than crash)
            existing = (
                db.query(Assessment)
                .filter(
                    Assessment.student_id == student.id,
                    Assessment.subject_id == subject.id,
                    Assessment.assessment_type == assessment_type,
                )
                .first()
            )
            if existing:
                raise ValueError(
                    f"Duplicate record for student='{sid_code}', "
                    f"subject='{subject_code}', type='{assessment_type}'."
                )

            assessment = Assessment(
                student_id=student.id,
                subject_id=subject.id,
                assessment_type=assessment_type,
                marks=marks,
                is_missing=is_missing,
            )
            db.add(assessment)
            db.commit()
            success_count += 1

        except Exception as exc:
            db.rollback()
            error_count += 1
            errors.append({"row": row_num, "message": str(exc)})

    return {
        "success_count": success_count,
        "error_count": error_count,
        "errors": errors,
    }
