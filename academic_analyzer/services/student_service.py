"""
Student Service — CRUD operations for Student model.
"""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from academic_analyzer.models import Student
from academic_analyzer.schemas import StudentCreate, StudentUpdate


def get_all_students(db: Session, search: Optional[str] = None) -> List[Student]:
    """Return all students, optionally filtered by name or student_id code."""
    query = db.query(Student)
    if search:
        like = f"%{search}%"
        query = query.filter(
            Student.name.ilike(like) | Student.student_id.ilike(like)
        )
    return query.order_by(Student.name).all()


def get_student_by_id(db: Session, student_id: int) -> Optional[Student]:
    """Return a Student by its primary-key id, or None."""
    return db.query(Student).filter(Student.id == student_id).first()


def get_student_by_student_code(db: Session, student_code: str) -> Optional[Student]:
    """Return a Student by the unique student_id string code, or None."""
    return db.query(Student).filter(Student.student_id == student_code).first()


def create_student(db: Session, student_data: StudentCreate) -> Student:
    """Create a new Student.  Raises HTTP 400 if student_id code already exists."""
    existing = get_student_by_student_code(db, student_data.student_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Student with student_id '{student_data.student_id}' already exists.",
        )
    student = Student(**student_data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def update_student(
    db: Session, student_id: int, student_data: StudentUpdate
) -> Student:
    """Update an existing Student.  Raises HTTP 404 if not found."""
    student = get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    update_data = student_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)
    return student


def delete_student(db: Session, student_id: int) -> bool:
    """Delete a Student.  Returns True on success, raises HTTP 404 if not found."""
    student = get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    db.delete(student)
    db.commit()
    return True


def get_students_by_department(db: Session, department: str) -> List[Student]:
    """Return all students in a given department (case-insensitive)."""
    return (
        db.query(Student)
        .filter(Student.department.ilike(department))
        .order_by(Student.name)
        .all()
    )
