# Integration tests for statistical analysis endpoints
# Tests that API returns proper structure with real data
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from statistical_analysis.interpretation import categorize_student, identify_at_risk_students


class TestInterpretation:
    def test_categorize_excellent(self):
        # marks=90, mean=70, std=10 → z=2 → Excellent
        cat = categorize_student(90, mean=70, std_dev=10)
        assert cat == "Excellent"

    def test_categorize_at_risk(self):
        # marks=40, mean=70, std=10 → z=-3 → Below Average
        cat = categorize_student(40, mean=70, std_dev=10)
        assert cat == "Below Average"

    def test_identify_at_risk(self):
        students = [
            {"student_id": "CS001", "name": "Alice", "marks": 80},
            {"student_id": "CS002", "name": "Bob", "marks": 30},  # z=-2.86 at-risk
        ]
        at_risk = identify_at_risk_students(students, mean=70, std_dev=10, threshold_z=-1.5)
        at_risk_ids = [s["student_id"] for s in at_risk]
        assert "CS002" in at_risk_ids
        assert "CS001" not in at_risk_ids
