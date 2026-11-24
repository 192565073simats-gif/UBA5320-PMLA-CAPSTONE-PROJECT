import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from statistical_analysis.descriptive import calculate_descriptive_stats, detect_outliers_iqr
from statistical_analysis.distributions import test_normality as run_test_normality, fit_normal_distribution, binomial_pass_fail, calculate_z_scores


class TestDescriptiveStats:
    def test_mean_calculation(self):
        marks = [70, 80, 90, 60, 50]
        result = calculate_descriptive_stats(marks)
        assert abs(result['mean'] - 70.0) < 0.001

    def test_median_odd_count(self):
        marks = [60, 70, 80, 90, 50]  # sorted: 50,60,70,80,90 → median=70
        result = calculate_descriptive_stats(marks)
        assert result['median'] == 70.0

    def test_median_even_count(self):
        marks = [60, 70, 80, 90]  # (70+80)/2 = 75
        result = calculate_descriptive_stats(marks)
        assert result['median'] == 75.0

    def test_std_deviation_known_values(self):
        # Population std dev of [2,4,4,4,5,5,7,9] = 2.0
        marks = [2, 4, 4, 4, 5, 5, 7, 9]
        result = calculate_descriptive_stats(marks)
        assert abs(result['std_dev'] - 2.0) < 0.001

    def test_range_calculation(self):
        marks = [45, 67, 89, 23, 78]
        result = calculate_descriptive_stats(marks)
        assert result['range_val'] == 89 - 23

    def test_empty_marks_handled(self):
        result = calculate_descriptive_stats([])
        assert result['count'] == 0

    def test_single_mark(self):
        result = calculate_descriptive_stats([75.0])
        assert result['mean'] == 75.0

    def test_outlier_detection_iqr(self):
        marks = [50, 55, 60, 65, 70, 75, 80, 10, 95]  # 10 is outlier
        outliers = detect_outliers_iqr(marks)
        assert 10 in outliers or len(outliers) > 0


class TestDistributions:
    def test_z_scores_known(self):
        marks = [70, 80, 90]  # mean=80, std≈8.165
        z_scores = calculate_z_scores(marks)
        assert len(z_scores) == 3
        assert abs(z_scores[1]) < 0.001  # middle value z≈0

    def test_binomial_pass_fail_counts(self):
        marks = [80, 90, 30, 25, 70, 85, 65]  # 5 pass, 2 fail (threshold=40)
        result = binomial_pass_fail(marks, pass_threshold=40, max_marks=100)
        assert result['n'] == 7
        assert abs(result['empirical_p'] - 5/7) < 0.001

    def test_normality_test_runs(self):
        import numpy as np
        np.random.seed(42)
        marks = list(np.random.normal(70, 10, 30))
        result = run_test_normality(marks)
        assert 'is_normal' in result
        assert 'p_value' in result
        assert 'interpretation' in result

    def test_normal_fit_returns_pdf(self):
        marks = [65, 70, 75, 80, 85, 70, 75, 65, 80, 72]
        result = fit_normal_distribution(marks)
        assert 'mean' in result
        assert 'std' in result
        assert len(result['pdf_x']) > 0


class TestEdgeCases:
    def test_all_same_marks(self):
        marks = [75, 75, 75, 75, 75]
        result = calculate_descriptive_stats(marks)
        assert result['std_dev'] == 0.0
        assert result['range_val'] == 0

    def test_two_marks(self):
        result = calculate_descriptive_stats([60, 80])
        assert result['mean'] == 70.0
