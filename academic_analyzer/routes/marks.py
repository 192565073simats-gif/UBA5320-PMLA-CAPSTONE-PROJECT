"""
routes/marks.py — CRUD endpoints for Assessment (marks) records.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from academic_analyzer.auth import get_current_user
from academic_analyzer.database import get_db
from academic_analyzer.models import Assessment, Student, Subject
from academic_analyzer.schemas import (
    AssessmentCreate,
    AssessmentOut,
    AssessmentUpdate,
    MessageResponse,
)

router = APIRouter()


def _get_assessment_or_404(assessment_id: int, db: Session) -> Assessment:
    record = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Assessment record not found")
    return record


@router.get("/", response_model=List[AssessmentOut])
def list_assessments(
    student_id: Optional[int] = Query(None),
    subject_id: Optional[int] = Query(None),
    assessment_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    q = db.query(Assessment)
    if student_id is not None:
        q = q.filter(Assessment.student_id == student_id)
    if subject_id is not None:
        q = q.filter(Assessment.subject_id == subject_id)
    if assessment_type:
        q = q.filter(Assessment.assessment_type == assessment_type)
    return q.offset(skip).limit(limit).all()


@router.post("/", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def create_assessment(
    assessment_in: AssessmentCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if not db.query(Student).filter(Student.id == assessment_in.student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    if not db.query(Subject).filter(Subject.id == assessment_in.subject_id).first():
        raise HTTPException(status_code=404, detail="Subject not found")

    existing = (
        db.query(Assessment)
        .filter(
            Assessment.student_id == assessment_in.student_id,
            Assessment.subject_id == assessment_in.subject_id,
            Assessment.assessment_type == assessment_in.assessment_type,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Assessment record already exists for student_id={assessment_in.student_id}, "
                f"subject_id={assessment_in.subject_id}, type={assessment_in.assessment_type!r}. "
                "Use PUT to update it."
            ),
        )

    is_missing = assessment_in.marks is None
    record = Assessment(
        **assessment_in.model_dump(),
        is_missing=is_missing,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return _get_assessment_or_404(assessment_id, db)


@router.put("/{assessment_id}", response_model=AssessmentOut)
def update_assessment(
    assessment_id: int,
    assessment_in: AssessmentUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    record = _get_assessment_or_404(assessment_id, db)
    update_data = assessment_in.model_dump(exclude_unset=True)
    if "marks" in update_data:
        update_data.setdefault("is_missing", update_data["marks"] is None)
    for field, value in update_data.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{assessment_id}", response_model=MessageResponse)
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    record = _get_assessment_or_404(assessment_id, db)
    db.delete(record)
    db.commit()
    return {"message": f"Assessment record {assessment_id} deleted successfully", "success": True}
