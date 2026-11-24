"""
services/report_service.py — PDF / CSV report generation and performance analysis.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from sqlalchemy.orm import Session

from academic_analyzer.models import Assessment, AnalysisReport, Student, Subject

# ---------------------------------------------------------------------------
# Local imports — guard against missing modules gracefully
# ---------------------------------------------------------------------------
try:
    from academic_analyzer.statistical_analysis.descriptive import (
        calculate_descriptive_stats, detect_outliers_iqr
    )
    from academic_analyzer.statistical_analysis.distributions import (
        test_normality, fit_normal_distribution, binomial_pass_fail, calculate_z_scores
    )
    from academic_analyzer.statistical_analysis.interpretation import (
        categorize_student, identify_at_risk_students,
        interpret_descriptive_stats, suggest_support
    )
except ImportError:
    # Fallback stubs so the module loads even when stat modules are partial
    def calculate_descriptive_stats(marks): return {}  # type: ignore
    def detect_outliers_iqr(marks): return [], marks  # type: ignore
    def test_normality(marks): return {}  # type: ignore
    def fit_normal_distribution(marks): return {}  # type: ignore
    def binomial_pass_fail(marks, pass_mark=40): return {}  # type: ignore
    def calculate_z_scores(marks): return []  # type: ignore
    def categorize_student(avg, max_mark=100): return "Average"  # type: ignore
    def identify_at_risk_students(scores, **kw): return []  # type: ignore
    def interpret_descriptive_stats(stats): return ""  # type: ignore
    def suggest_support(cat, z=None): return []  # type: ignore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports"
)
os.makedirs(REPORTS_DIR, exist_ok=True)

BRAND_BLUE = colors.HexColor("#1a73e8")
BRAND_LIGHT = colors.HexColor("#e8f0fe")
BRAND_ALT = colors.HexColor("#f8f9fa")
PASS_MARK = 40.0


# ===========================================================================
# Internal helpers
# ===========================================================================

def _get_all_exam_marks(db: Session, subject_id: Optional[int] = None,
                         department: Optional[str] = None) -> List[float]:
    q = db.query(Assessment).filter(
        Assessment.assessment_type == "exam",
        Assessment.marks.isnot(None),
    )
    if subject_id:
        q = q.filter(Assessment.subject_id == subject_id)
    if department:
        q = q.join(Student).filter(Student.department == department)
    return [a.marks for a in q.all()]


def _percentile_rank(value: float, all_values: List[float]) -> float:
    if not all_values:
        return 0.0
    below = sum(1 for v in all_values if v < value)
    return round((below / len(all_values)) * 100, 1)


def _build_pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="HeaderTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="HeaderSub",
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=BRAND_BLUE,
        spaceBefore=14,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="BodySmall",
        fontName="Helvetica",
        fontSize=9,
        spaceAfter=4,
    ))
    return styles


def _header_table(title: str, subtitle: str, styles) -> Table:
    data = [
        [Paragraph(title, styles["HeaderTitle"])],
        [Paragraph(subtitle, styles["HeaderSub"])],
        [Paragraph(
            f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}",
            styles["HeaderSub"]
        )],
    ]
    t = Table(data, colWidths=[17 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
        ("BOX", (0, 0), (-1, -1), 1, BRAND_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _styled_table(headers: List[str], rows: List[List[Any]],
                  col_widths: Optional[List] = None) -> Table:
    table_data = [headers] + rows
    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        # Data rows
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dee2e6")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_ALT]),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t


# ===========================================================================
# Performance data builders
# ===========================================================================

def get_student_performance(db: Session, student_id: int) -> Dict[str, Any]:
    """Return complete performance data for one student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {"error": f"Student id={student_id} not found"}

    assessments = (
        db.query(Assessment)
        .filter(Assessment.student_id == student_id, Assessment.marks.isnot(None))
        .all()
    )

    # Collect marks per subject
    subject_map: Dict[int, Dict[str, Any]] = {}
    for a in assessments:
        sid = a.subject_id
        if sid not in subject_map:
            subj = db.query(Subject).filter(Subject.id == sid).first()
            subject_map[sid] = {
                "subject_id": sid,
                "subject_name": subj.subject_name if subj else f"Subject {sid}",
                "subject_code": subj.subject_code if subj else "",
                "max_marks": subj.max_marks if subj else 100.0,
                "internal": None,
                "exam": None,
            }
        subject_map[sid][a.assessment_type] = a.marks

    # Class-wide exam marks for z-score computation
    all_exam_marks = _get_all_exam_marks(db)
    z_scores_all = calculate_z_scores(all_exam_marks) if all_exam_marks else []

    subjects_detail: List[Dict[str, Any]] = []
    all_student_marks: List[float] = []

    for subj_data in subject_map.values():
        marks_list = [m for m in [subj_data["internal"], subj_data["exam"]] if m is not None]
        mean_subj = float(np.mean(marks_list)) if marks_list else 0.0

        # Subject-level class marks for comparison
        subj_exam_marks = _get_all_exam_marks(db, subject_id=subj_data["subject_id"])
        subj_stats = calculate_descriptive_stats(subj_exam_marks)
        class_mean = subj_stats.get("mean") or 0.0

        exam_mark = subj_data.get("exam")
        z = None
        percentile = None
        if exam_mark is not None and subj_exam_marks:
            zs = calculate_z_scores(subj_exam_marks)
            idx = None
            # find this student's exam mark index
            matching = [
                i for i, a in enumerate(
                    db.query(Assessment)
                    .filter(Assessment.subject_id == subj_data["subject_id"],
                            Assessment.assessment_type == "exam",
                            Assessment.marks.isnot(None))
                    .all()
                )
                if a.student_id == student_id
            ]
            if matching:
                idx = matching[0]
                z = zs[idx] if idx < len(zs) else None
            percentile = _percentile_rank(exam_mark, subj_exam_marks)

        category = categorize_student(mean_subj, subj_data["max_marks"])
        all_student_marks.extend(marks_list)

        subjects_detail.append({
            "subject_id": subj_data["subject_id"],
            "subject_name": subj_data["subject_name"],
            "subject_code": subj_data["subject_code"],
            "internal_marks": subj_data["internal"],
            "exam_marks": subj_data["exam"],
            "average": round(mean_subj, 2),
            "class_mean": round(class_mean, 2),
            "z_score": round(z, 3) if z is not None else None,
            "percentile_rank": percentile,
            "category": category,
        })

    overall_avg = float(np.mean(all_student_marks)) if all_student_marks else 0.0
    overall_category = categorize_student(overall_avg)

    # Overall z-score
    overall_z = None
    if all_exam_marks:
        exam_marks_student = [s["exam_marks"] for s in subjects_detail if s["exam_marks"] is not None]
        if exam_marks_student:
            student_avg_exam = float(np.mean(exam_marks_student))
            zs = calculate_z_scores(all_exam_marks)
            # Approximate: compute based on student mean vs class
            mu = float(np.mean(all_exam_marks))
            std = float(np.std(all_exam_marks, ddof=1)) if len(all_exam_marks) > 1 else 1
            overall_z = (student_avg_exam - mu) / std if std else 0.0

    at_risk = overall_avg < PASS_MARK or (overall_z is not None and overall_z < -1.5)
    risk_reasons: List[str] = []
    if overall_avg < PASS_MARK:
        risk_reasons.append(f"Overall average {overall_avg:.1f} below pass mark")
    if overall_z is not None and overall_z < -1.5:
        risk_reasons.append(f"z-score {overall_z:.2f} below threshold")

    suggestions = suggest_support(overall_category, overall_z)

    return {
        "student": {
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "department": student.department,
            "year": student.year,
            "semester": student.semester,
            "email": student.email,
        },
        "subjects": subjects_detail,
        "overall_average": round(overall_avg, 2),
        "overall_category": overall_category,
        "overall_z_score": round(overall_z, 3) if overall_z is not None else None,
        "at_risk": at_risk,
        "risk_reasons": risk_reasons,
        "support_suggestions": suggestions,
    }


def get_class_performance(
    db: Session,
    subject_id: Optional[int] = None,
    department: Optional[str] = None,
) -> Dict[str, Any]:
    """Return class-wide performance analysis."""
    q = db.query(Assessment).filter(
        Assessment.marks.isnot(None),
        Assessment.assessment_type == "exam",
    )
    if subject_id:
        q = q.filter(Assessment.subject_id == subject_id)
    if department:
        q = q.join(Student).filter(Student.department == department)

    assessments = q.all()
    all_marks = [a.marks for a in assessments]

    overall_stats = calculate_descriptive_stats(all_marks)
    normality = test_normality(all_marks)
    binomial = binomial_pass_fail(all_marks, PASS_MARK)
    interpretation = interpret_descriptive_stats(overall_stats)

    # Per-subject breakdown
    subject_ids = list({a.subject_id for a in assessments})
    subjects_q = db.query(Subject).filter(Subject.id.in_(subject_ids)).all()
    subjects_dict = {s.id: s for s in subjects_q}

    subject_breakdown: List[Dict[str, Any]] = []
    for sid in subject_ids:
        subj_marks = [a.marks for a in assessments if a.subject_id == sid]
        s = subjects_dict.get(sid)
        stats = calculate_descriptive_stats(subj_marks)
        subject_breakdown.append({
            "subject_id": sid,
            "subject_name": s.subject_name if s else f"Subject {sid}",
            "subject_code": s.subject_code if s else "",
            "stats": stats,
            "pass_rate": round(
                sum(1 for m in subj_marks if m >= PASS_MARK) / len(subj_marks) * 100, 1
            ) if subj_marks else 0.0,
        })
    subject_breakdown.sort(key=lambda x: x["stats"].get("mean") or 0, reverse=True)

    # Category distribution
    z_scores = calculate_z_scores(all_marks)
    category_counts: Dict[str, int] = {
        "Excellent": 0, "Good": 0, "Average": 0, "Below Average": 0
    }

    # Per-student averages for at-risk and category analysis
    student_ids = list({a.student_id for a in assessments})
    student_entries: List[Dict[str, Any]] = []
    students_q = db.query(Student).filter(Student.id.in_(student_ids)).all()
    students_dict = {s.id: s for s in students_q}

    for stu_id in student_ids:
        stu_marks = [a.marks for a in assessments if a.student_id == stu_id]
        avg = float(np.mean(stu_marks)) if stu_marks else 0.0
        cat = categorize_student(avg)
        category_counts[cat] = category_counts.get(cat, 0) + 1

        z = None
        if all_marks and len(all_marks) > 1:
            mu = float(np.mean(all_marks))
            std = float(np.std(all_marks, ddof=1))
            z = (avg - mu) / std if std else 0.0

        stu = students_dict.get(stu_id)
        student_entries.append({
            "student_id": stu_id,
            "student_code": stu.student_id if stu else str(stu_id),
            "name": stu.name if stu else f"Student {stu_id}",
            "department": stu.department if stu else "",
            "average_marks": round(avg, 2),
            "z_score": round(z, 3) if z is not None else None,
            "category": cat,
        })

    at_risk_list = identify_at_risk_students(student_entries, z_threshold=-1.5, pass_mark=PASS_MARK)
    top_performers = sorted(student_entries, key=lambda x: x["average_marks"], reverse=True)[:10]

    return {
        "overall_stats": overall_stats,
        "normality_test": normality,
        "binomial_analysis": binomial,
        "interpretation": interpretation,
        "subject_breakdown": subject_breakdown,
        "category_distribution": category_counts,
        "at_risk_students": at_risk_list,
        "top_performers": top_performers,
        "subject_rankings": [
            {"rank": i + 1, "subject_name": s["subject_name"],
             "mean": s["stats"].get("mean"), "pass_rate": s["pass_rate"]}
            for i, s in enumerate(subject_breakdown)
        ],
        "total_students": len(student_ids),
        "total_assessments": len(assessments),
    }


# ===========================================================================
# PDF report generator
# ===========================================================================

def generate_pdf_report(
    db: Session,
    report_type: str,
    filters: Dict[str, Any],
    generated_by_id: int,
) -> str:
    """Generate a professional PDF report and return its file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report_type}_report_{timestamp}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    styles = _build_pdf_styles()
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    story = []

    if report_type == "student":
        student_id = filters.get("student_id")
        data = get_student_performance(db, student_id)
        _build_student_pdf(story, data, styles)

    elif report_type == "class":
        subject_id = filters.get("subject_id")
        department = filters.get("department")
        data = get_class_performance(db, subject_id=subject_id, department=department)
        _build_class_pdf(story, data, styles, filters)

    else:
        raise ValueError(f"Unknown report_type: {report_type!r}")

    doc.build(story)
    return filepath


def _build_student_pdf(story, data: Dict[str, Any], styles):
    if "error" in data:
        story.append(Paragraph(data["error"], styles["Normal"]))
        return

    stu = data["student"]
    story.append(_header_table(
        "Statistical Analysis of Student Academic Performance",
        f"Student Report — {stu['name']} ({stu['student_id']})",
        styles,
    ))
    story.append(Spacer(1, 0.4 * cm))

    # Student info
    story.append(Paragraph("Student Information", styles["SectionTitle"]))
    info_rows = [
        ["Name", stu["name"], "Student ID", stu["student_id"]],
        ["Department", stu["department"], "Year / Semester", f"Year {stu['year']}, Sem {stu['semester']}"],
        ["Email", stu.get("email") or "—", "Overall Category", data["overall_category"]],
        ["Overall Average", f"{data['overall_average']:.1f}", "At Risk", "Yes ✗" if data["at_risk"] else "No ✓"],
    ]
    story.append(_styled_table(
        ["Field", "Value", "Field", "Value"],
        info_rows,
        col_widths=[4 * cm, 4.5 * cm, 4 * cm, 4.5 * cm],
    ))
    story.append(Spacer(1, 0.3 * cm))

    # Subject marks
    story.append(Paragraph("Subject-wise Performance", styles["SectionTitle"]))
    subj_rows = []
    for s in data["subjects"]:
        subj_rows.append([
            s["subject_code"],
            s["subject_name"],
            str(s["internal_marks"] if s["internal_marks"] is not None else "—"),
            str(s["exam_marks"] if s["exam_marks"] is not None else "—"),
            f"{s['average']:.1f}",
            f"{s['class_mean']:.1f}",
            f"{s['z_score']:.2f}" if s["z_score"] is not None else "—",
            f"{s['percentile_rank']:.0f}%" if s["percentile_rank"] is not None else "—",
            s["category"],
        ])
    story.append(_styled_table(
        ["Code", "Subject", "Internal", "Exam", "Avg", "Class Avg", "Z-Score", "Percentile", "Category"],
        subj_rows,
        col_widths=[1.6*cm, 4*cm, 1.5*cm, 1.5*cm, 1.4*cm, 1.9*cm, 1.6*cm, 1.8*cm, 2.7*cm],
    ))
    story.append(Spacer(1, 0.3 * cm))

    # At-risk + suggestions
    if data["at_risk"]:
        story.append(Paragraph("⚠ At-Risk Indicators", styles["SectionTitle"]))
        for r in data["risk_reasons"]:
            story.append(Paragraph(f"• {r}", styles["BodySmall"]))
        story.append(Spacer(1, 0.2 * cm))

    story.append(Paragraph("Support Suggestions (For Teacher Review)", styles["SectionTitle"]))
    for s in data["support_suggestions"]:
        story.append(Paragraph(f"• {s}", styles["BodySmall"]))


def _build_class_pdf(story, data: Dict[str, Any], styles, filters: Dict[str, Any]):
    subtitle = "Class Performance Report"
    if filters.get("department"):
        subtitle += f" — {filters['department']} Dept"
    if filters.get("subject_id"):
        subtitle += f" — Subject #{filters['subject_id']}"

    story.append(_header_table(
        "Statistical Analysis of Student Academic Performance",
        subtitle,
        styles,
    ))
    story.append(Spacer(1, 0.4 * cm))

    # Overall stats
    story.append(Paragraph("Overall Class Statistics", styles["SectionTitle"]))
    s = data["overall_stats"]
    stat_rows = [
        ["Total Students", str(data["total_students"]), "Total Assessments", str(data["total_assessments"])],
        ["Mean", f"{s.get('mean', 0):.2f}" if s.get('mean') else "—",
         "Median", f"{s.get('median', 0):.2f}" if s.get('median') else "—"],
        ["Std Deviation", f"{s.get('std_dev', 0):.2f}" if s.get('std_dev') else "—",
         "Variance", f"{s.get('variance', 0):.2f}" if s.get('variance') else "—"],
        ["Min", f"{s.get('min_val', 0):.1f}" if s.get('min_val') is not None else "—",
         "Max", f"{s.get('max_val', 0):.1f}" if s.get('max_val') is not None else "—"],
        ["Skewness", f"{s.get('skewness', 0):.3f}" if s.get('skewness') is not None else "—",
         "Kurtosis", f"{s.get('kurtosis', 0):.3f}" if s.get('kurtosis') is not None else "—"],
    ]
    story.append(_styled_table(
        ["Metric", "Value", "Metric", "Value"],
        stat_rows,
        col_widths=[4*cm, 4.5*cm, 4*cm, 4.5*cm],
    ))
    story.append(Spacer(1, 0.3 * cm))

    # Normality test
    story.append(Paragraph("Normality Test (Shapiro-Wilk)", styles["SectionTitle"]))
    nt = data["normality_test"]
    norm_rows = [
        ["Test Statistic", f"{nt.get('statistic', 'N/A'):.4f}" if nt.get("statistic") else "N/A",
         "p-value", f"{nt.get('p_value', 'N/A'):.4f}" if nt.get("p_value") else "N/A"],
        ["Normally Distributed", "Yes" if nt.get("is_normal") else "No",
         "Interpretation", nt.get("interpretation", "")[:60]],
    ]
    story.append(_styled_table(
        ["Metric", "Value", "Metric", "Value"],
        norm_rows,
        col_widths=[4*cm, 4.5*cm, 4*cm, 4.5*cm],
    ))
    story.append(Spacer(1, 0.3 * cm))

    # Category distribution
    story.append(Paragraph("Performance Category Distribution", styles["SectionTitle"]))
    cat = data["category_distribution"]
    total = sum(cat.values()) or 1
    cat_rows = [[k, str(v), f"{v/total*100:.1f}%"] for k, v in cat.items()]
    story.append(_styled_table(
        ["Category", "Count", "Percentage"],
        cat_rows,
        col_widths=[5*cm, 3*cm, 4*cm],
    ))
    story.append(Spacer(1, 0.3 * cm))

    # Subject rankings
    story.append(Paragraph("Subject Rankings by Mean Score", styles["SectionTitle"]))
    rank_rows = [
        [str(r["rank"]), r["subject_name"],
         f"{r['mean']:.2f}" if r["mean"] else "—",
         f"{r['pass_rate']:.1f}%"]
        for r in data["subject_rankings"]
    ]
    story.append(_styled_table(
        ["Rank", "Subject", "Mean Score", "Pass Rate"],
        rank_rows,
        col_widths=[1.5*cm, 8*cm, 3.5*cm, 4*cm],
    ))
    story.append(Spacer(1, 0.3 * cm))

    # At-risk students
    if data["at_risk_students"]:
        story.append(Paragraph("At-Risk Students", styles["SectionTitle"]))
        at_rows = [
            [s["student_code"], s["name"], s["department"],
             f"{s['average_marks']:.1f}",
             f"{s['z_score']:.2f}" if s["z_score"] is not None else "—",
             "; ".join(s.get("risk_reasons", []))[:60]]
            for s in data["at_risk_students"]
        ]
        story.append(_styled_table(
            ["ID", "Name", "Dept", "Avg", "Z-Score", "Risk Reason"],
            at_rows,
            col_widths=[2*cm, 4*cm, 2.5*cm, 1.5*cm, 1.8*cm, 5.2*cm],
        ))
        story.append(Spacer(1, 0.3 * cm))

    # Interpretation
    story.append(Paragraph("Statistical Interpretation", styles["SectionTitle"]))
    story.append(Paragraph(data["interpretation"], styles["BodySmall"]))


# ===========================================================================
# CSV report generator
# ===========================================================================

def generate_csv_report(
    db: Session,
    report_type: str,
    filters: Dict[str, Any],
) -> str:
    """Generate a CSV export and return its file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report_type}_report_{timestamp}.csv"
    filepath = os.path.join(REPORTS_DIR, filename)

    if report_type == "student":
        student_id = filters.get("student_id")
        perf = get_student_performance(db, student_id)
        rows = []
        for s in perf.get("subjects", []):
            rows.append({
                "student_id": perf["student"]["student_id"],
                "student_name": perf["student"]["name"],
                "department": perf["student"]["department"],
                "year": perf["student"]["year"],
                "semester": perf["student"]["semester"],
                "subject_code": s["subject_code"],
                "subject_name": s["subject_name"],
                "internal_marks": s["internal_marks"],
                "exam_marks": s["exam_marks"],
                "average": s["average"],
                "class_mean": s["class_mean"],
                "z_score": s["z_score"],
                "percentile_rank": s["percentile_rank"],
                "category": s["category"],
            })
        df = pd.DataFrame(rows)

    elif report_type == "class":
        subject_id = filters.get("subject_id")
        department = filters.get("department")
        perf = get_class_performance(db, subject_id=subject_id, department=department)
        rows = []
        for entry in perf.get("top_performers", []) + perf.get("at_risk_students", []):
            rows.append({
                "student_code": entry.get("student_code"),
                "name": entry.get("name"),
                "department": entry.get("department"),
                "average_marks": entry.get("average_marks"),
                "z_score": entry.get("z_score"),
                "category": entry.get("category"),
                "at_risk": entry.get("at_risk", False),
            })
        # Deduplicate
        df = pd.DataFrame(rows).drop_duplicates(subset=["student_code"])

    else:
        raise ValueError(f"Unknown report_type: {report_type!r}")

    df.to_csv(filepath, index=False)
    return filepath
