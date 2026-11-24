"""
schemas.py — Pydantic v2 request/response schemas for the Academic Analyzer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ===========================================================================
# Auth / User
# ===========================================================================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


# ===========================================================================
# Student
# ===========================================================================

class StudentCreate(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1, le=6)
    semester: int = Field(..., ge=1, le=12)
    email: Optional[EmailStr] = None


class StudentUpdate(BaseModel):
    student_id: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1, le=6)
    semester: Optional[int] = Field(None, ge=1, le=12)
    email: Optional[EmailStr] = None


class StudentOut(StudentCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# Subject
# ===========================================================================

class SubjectCreate(BaseModel):
    subject_code: str = Field(..., min_length=1, max_length=50)
    subject_name: str = Field(..., min_length=1, max_length=255)
    max_marks: float = Field(default=100.0, ge=0)
    min_marks: float = Field(default=0.0, ge=0)
    department: str = Field(..., min_length=1, max_length=100)

    @field_validator("max_marks")
    @classmethod
    def max_gt_min(cls, v: float, info: Any) -> float:
        # min_marks may not yet be in info.data if validation order differs,
        # so guard with a check.
        min_m = info.data.get("min_marks", 0.0)
        if min_m is not None and v <= min_m:
            raise ValueError("max_marks must be greater than min_marks")
        return v


class SubjectUpdate(BaseModel):
    subject_code: Optional[str] = Field(None, min_length=1, max_length=50)
    subject_name: Optional[str] = Field(None, min_length=1, max_length=255)
    max_marks: Optional[float] = Field(None, ge=0)
    min_marks: Optional[float] = Field(None, ge=0)
    department: Optional[str] = Field(None, min_length=1, max_length=100)


class SubjectOut(SubjectCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# Assessment
# ===========================================================================

VALID_ASSESSMENT_TYPES = {"internal", "exam"}


class AssessmentCreate(BaseModel):
    student_id: int
    subject_id: int
    assessment_type: str = Field(..., pattern="^(internal|exam)$")
    marks: Optional[float] = Field(None, ge=0)
    remarks: Optional[str] = Field(None, max_length=500)

    @field_validator("assessment_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_ASSESSMENT_TYPES:
            raise ValueError(f"assessment_type must be one of {VALID_ASSESSMENT_TYPES}")
        return v


class AssessmentUpdate(BaseModel):
    assessment_type: Optional[str] = Field(None, pattern="^(internal|exam)$")
    marks: Optional[float] = Field(None, ge=0)
    is_missing: Optional[bool] = None
    remarks: Optional[str] = Field(None, max_length=500)


class AssessmentOut(BaseModel):
    id: int
    student_id: int
    subject_id: int
    assessment_type: str
    marks: Optional[float]
    is_missing: bool
    remarks: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# Statistical Analysis
# ===========================================================================

class StatsSummary(BaseModel):
    mean: Optional[float] = None
    median: Optional[float] = None
    mode: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    range_val: Optional[float] = None
    variance: Optional[float] = None
    std_dev: Optional[float] = None
    count: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None


class AnalysisResult(BaseModel):
    subject_id: int
    subject_name: str
    stats: StatsSummary
    normal_fit: Dict[str, Any] = Field(default_factory=dict)
    distribution_type: str
    interpretation: str


# ===========================================================================
# Reports
# ===========================================================================

class ReportOut(BaseModel):
    id: int
    report_name: str
    report_type: str
    created_at: datetime
    file_path: Optional[str] = None

    model_config = {"from_attributes": True}


# ===========================================================================
# Generic helpers
# ===========================================================================

class MessageResponse(BaseModel):
    """Generic success/error message envelope."""
    message: str
    success: bool = True


class PaginatedResponse(BaseModel):
    """Generic paginated list wrapper."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
