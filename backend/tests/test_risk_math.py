"""Pure unit tests for the risk feature/label math (no DB, no XGBoost)."""

from app.models.prediction import RiskLevel
from app.services import risk_math


def test_feature_names_are_the_five_fixed_features():
    assert risk_math.FEATURE_NAMES == (
        "attendance_percentage",
        "quiz_average_percentage",
        "assignment_average_percentage",
        "midterm_score_percentage",
        "current_avg_clo_attainment",
    )


def test_assemble_feature_row_orders_by_feature_names():
    row = risk_math.assemble_feature_row(
        {
            "current_avg_clo_attainment": 5.0,
            "attendance_percentage": 1.0,
            "quiz_average_percentage": 2.0,
            "assignment_average_percentage": 3.0,
            "midterm_score_percentage": 4.0,
        }
    )
    assert row == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_assemble_feature_row_defaults_missing_to_zero():
    # A student with no recorded attendance still yields a usable row.
    row = risk_math.assemble_feature_row({"quiz_average_percentage": 50.0})
    assert row[0] == 0.0  # attendance missing -> 0.0
    assert row[1] == 50.0


def test_assemble_feature_row_clamps_out_of_range():
    row = risk_math.assemble_feature_row(
        {name: 250.0 for name in risk_math.FEATURE_NAMES}
    )
    assert all(value == 100.0 for value in row)
    row = risk_math.assemble_feature_row(
        {name: -30.0 for name in risk_math.FEATURE_NAMES}
    )
    assert all(value == 0.0 for value in row)


def test_risk_level_buckets():
    assert risk_math.risk_level_from_score(0.0) is RiskLevel.high
    assert risk_math.risk_level_from_score(49.9) is RiskLevel.high
    assert risk_math.risk_level_from_score(50.0) is RiskLevel.medium
    assert risk_math.risk_level_from_score(69.9) is RiskLevel.medium
    assert risk_math.risk_level_from_score(70.0) is RiskLevel.low
    assert risk_math.risk_level_from_score(100.0) is RiskLevel.low


def test_impact_label_direction():
    assert risk_math.impact_label(0.4) == "increased_risk"
    assert risk_math.impact_label(0.0) == "increased_risk"
    assert risk_math.impact_label(-0.1) == "decreased_risk"


def test_min_records_gate():
    assert risk_math.MIN_ASSESSMENT_RECORDS == 5
    assert risk_math.has_enough_records(5) is True
    assert risk_math.has_enough_records(6) is True
    assert risk_math.has_enough_records(4) is False
    assert risk_math.has_enough_records(0) is False
