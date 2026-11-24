"""
routes/reports.py — Report generation and listing endpoints.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from academic_analyzer.auth import get_current_user
from academic_analyzer.database import get_db
from academic_analyzer.models import AnalysisReport
from academic_analyzer.schemas import ReportOut

router = APIRouter()

REPORTS_DIR = Path("reports")


@router.get("/", response_model=List[ReportOut])
def list_reports(
    report_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    q = db.query(AnalysisReport)
    if report_type:
        q = q.filter(AnalysisReport.report_type == report_type)
    return q.order_by(AnalysisReport.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/", response_model=ReportOut, status_code=201)
def create_report_record(
    report_name: str = Query(...),
    report_type: str = Query(...),
    filters_applied: Optional[str] = Query(None, description="JSON string of filters"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a metadata record for a generated report."""
    report = AnalysisReport(
        report_name=report_name,
        report_type=report_type,
        generated_by=current_user.id,
        filters_applied=filters_applied or json.dumps({}),
        file_path=None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    # Remove file if present
    if report.file_path:
        try:
            Path(report.file_path).unlink(missing_ok=True)
        except Exception:
            pass
    db.delete(report)
    db.commit()
    return {"message": f"Report {report_id} deleted", "success": True}
