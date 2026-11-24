"""
routes/subjects.py — CRUD endpoints for Subject records.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from academic_analyzer.auth import get_current_user
from academic_analyzer.database import get_db
from academic_analyzer.models import Subject
from academic_analyzer.schemas import MessageResponse, SubjectCreate, SubjectOut, SubjectUpdate

router = APIRouter()


def _get_subject_or_404(subject_id: int, db: Session) -> Subject:
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router.get("/", response_model=List[SubjectOut])
def list_subjects(
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    q = db.query(Subject)
    if department:
        q = q.filter(Subject.department == department)
    if search:
        like = f"%{search}%"
        q = q.filter(
            Subject.subject_name.ilike(like) | Subject.subject_code.ilike(like)
        )
    return q.offset(skip).limit(limit).all()


@router.post("/", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(
    subject_in: SubjectCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if db.query(Subject).filter(Subject.subject_code == subject_in.subject_code).first():
        raise HTTPException(status_code=400, detail="Subject code already exists")
    subject = Subject(**subject_in.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return _get_subject_or_404(subject_id, db)


@router.put("/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: int,
    subject_in: SubjectUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    subject = _get_subject_or_404(subject_id, db)
    update_data = subject_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subject, field, value)
    db.commit()
    db.refresh(subject)
    return subject


@router.delete("/{subject_id}", response_model=MessageResponse)
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    subject = _get_subject_or_404(subject_id, db)
    db.delete(subject)
    db.commit()
    return {"message": f"Subject {subject.subject_code} deleted successfully", "success": True}
