"""Pure-function tests for the attainment formulas in CLAUDE.md section 8.

No database, no HTTP -- just the arithmetic and its edge cases.
"""

import pytest

from app.services import attainment_math


class TestCLOAttainment:
    def test_basic_percentage(self):
        assert attainment_math.clo_attainment(15.0, 20.0) == 75.0

    def test_full_marks(self):
        assert attainment_math.clo_attainment(20.0, 20.0) == 100.0

    def test_zero_obtained(self):
        assert attainment_math.clo_attainment(0.0, 20.0) == 0.0

    def test_rounds_to_two_decimals(self):
        # 2/3 -> 66.666... -> 66.67
        assert attainment_math.clo_attainment(2.0, 3.0) == 66.67

    @pytest.mark.parametrize("possible", [0.0, 0, -5.0])
    def test_zero_or_negative_possible_returns_zero_not_error(self, possible):
        """Section 8: division by zero must yield 0.00, never an exception."""
        assert attainment_math.clo_attainment(10.0, possible) == 0.0

    def test_zero_possible_logs_warning(self, caplog):
        with caplog.at_level("WARNING"):
            attainment_math.clo_attainment(0.0, 0.0)
        assert "non-positive possible marks" in caplog.text


class TestPLOAttainment:
    def test_weighted_average_by_strength(self):
        # (80*3 + 50*1) / (3+1) = 290/4 = 72.5
        assert attainment_math.plo_attainment([(80.0, 3), (50.0, 1)]) == 72.5

    def test_single_contribution(self):
        assert attainment_math.plo_attainment([(64.0, 2)]) == 64.0

    def test_equal_strengths_is_plain_mean(self):
        assert attainment_math.plo_attainment([(40.0, 2), (60.0, 2)]) == 50.0

    def test_strength_three_dominates(self):
        # (90*3 + 30*1) / 4 = 300/4 = 75.0
        assert attainment_math.plo_attainment([(90.0, 3), (30.0, 1)]) == 75.0

    def test_empty_contributions_returns_zero(self):
        """Section 8: Sum(Strength) = 0 must yield 0.00."""
        assert attainment_math.plo_attainment([]) == 0.0

    def test_zero_strengths_returns_zero(self):
        assert attainment_math.plo_attainment([(90.0, 0), (80.0, 0)]) == 0.0

    def test_zero_strength_logs_warning(self, caplog):
        with caplog.at_level("WARNING"):
            attainment_math.plo_attainment([])
        assert "total mapping strength" in caplog.text

    def test_rounds_to_two_decimals(self):
        # (70*1 + 80*2) / 3 = 230/3 = 76.666... -> 76.67
        assert attainment_math.plo_attainment([(70.0, 1), (80.0, 2)]) == 76.67


class TestClassAverage:
    def test_mean_of_cohort(self):
        assert attainment_math.class_average([100.0, 50.0, 0.0]) == 50.0

    def test_absent_students_drag_average_down(self):
        """Absentees score 0 and stay in the denominator (section 8)."""
        present_only = attainment_math.class_average([100.0, 100.0])
        with_absentee = attainment_math.class_average([100.0, 100.0, 0.0])
        assert present_only == 100.0
        assert with_absentee == 66.67

    def test_empty_cohort_returns_zero(self):
        assert attainment_math.class_average([]) == 0.0

    def test_empty_cohort_logs_warning(self, caplog):
        with caplog.at_level("WARNING"):
            attainment_math.class_average([])
        assert "no enrolled students" in caplog.text


class TestIsAchieved:
    def test_above_threshold(self):
        assert attainment_math.is_achieved(75.0, 50.0) is True

    def test_exactly_at_threshold_counts_as_achieved(self):
        assert attainment_math.is_achieved(50.0, 50.0) is True

    def test_below_threshold(self):
        assert attainment_math.is_achieved(49.99, 50.0) is False

    def test_custom_threshold(self):
        assert attainment_math.is_achieved(60.0, 70.0) is False
        assert attainment_math.is_achieved(70.0, 70.0) is True
