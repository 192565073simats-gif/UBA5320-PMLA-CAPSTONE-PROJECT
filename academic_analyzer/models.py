"""
models.py — SQLAlchemy ORM models for the Academic Analyzer application.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from academic_analyzer.database import Base


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    reports = relationship("AnalysisReport", back_populates="generator", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    assessments = relationship(
        "Assessment", back_populates="student", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Student id={self.id} student_id={self.student_id!r} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------
class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    subject_code = Column(String(50), unique=True, nullable=False, index=True)
    subject_name = Column(String(255), nullable=False)
    max_marks = Column(Float, default=100.0, nullable=False)
    min_marks = Column(Float, default=0.0, nullable=False)
    department = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    assessments = relationship(
        "Assessment", back_populates="subject", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Subject id={self.id} code={self.subject_code!r} name={self.subject_name!r}>"


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------
class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_type = Column(String(20), nullable=False)  # "internal" or "exam"
    marks = Column(Float, nullable=True)
    is_missing = Column(Boolean, default=False, nullable=False)
    remarks = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "assessment_type", name="uq_student_subject_type"),
    )

    # Relationships
    student = relationship("Student", back_populates="assessments")
    subject = relationship("Subject", back_populates="assessments")

    def __repr__(self) -> str:
        return (
            f"<Assessment id={self.id} student_id={self.student_id} "
            f"subject_id={self.subject_id} type={self.assessment_type!r} marks={self.marks}>"
        )


# ---------------------------------------------------------------------------
# AnalysisReport
# ---------------------------------------------------------------------------
class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_name = Column(String(255), nullable=False)
    report_type = Column(String(100), nullable=False)
    generated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filters_applied = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    file_path = Column(String(512), nullable=True)

    # Relationships
    generator = relationship("User", back_populates="reports")

    def __repr__(self) -> str:
        return f"<AnalysisReport id={self.id} name={self.report_name!r} type={self.report_type!r}>"
