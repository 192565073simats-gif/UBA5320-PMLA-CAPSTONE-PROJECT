"""
routes/students.py — CRUD endpoints for Student records.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from academic_analyzer.auth import get_current_user
from academic_analyzer.database import get_db
from academic_analyzer.models import Student
from academic_analyzer.schemas import MessageResponse, StudentCreate, StudentOut, StudentUpdate

router = APIRouter()


def _get_student_or_404(student_id: int, db: Session) -> Student:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/", response_model=List[StudentOut])
def list_students(
    department: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    semester: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    q = db.query(Student)
    if department:
        q = q.filter(Student.department == department)
    if year is not None:
        q = q.filter(Student.year == year)
    if semester is not None:
        q = q.filter(Student.semester == semester)
    if search:
        like = f"%{search}%"
        q = q.filter(
            Student.name.ilike(like) | Student.student_id.ilike(like)
        )
    return q.offset(skip).limit(limit).all()


@router.post("/", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(
    student_in: StudentCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if db.query(Student).filter(Student.student_id == student_in.student_id).first():
        raise HTTPException(status_code=400, detail="Student ID already exists")
    student = Student(**student_in.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentOut)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return _get_student_or_404(student_id, db)


@router.put("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    student_in: StudentUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    student = _get_student_or_404(student_id, db)
    update_data = student_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", response_model=MessageResponse)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    student = _get_student_or_404(student_id, db)
    db.delete(student)
    db.commit()
    return {"message": f"Student {student.student_id} deleted successfully", "success": True}
