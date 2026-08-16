"""Pure risk-prediction mathematics (CLAUDE.md section 9).

Deliberately free of database, XGBoost and SHAP imports so the feature-vector
assembly, bucketing and gap-detection rules can be unit-tested in isolation --
the same discipline `attainment_math.py` follows. The actual model lives in
`app/ml/risk_model.py`; this module only shapes its inputs and labels its
outputs.
"""

from app.models.prediction import RiskLevel

# The five numeric features, in the fixed order the model was trained on
# (CLAUDE.md section 9). Order is load-bearing: the feature row, the SHAP
# payload and the trained model all index by this sequence.
FEATURE_NAMES: tuple[str, ...] = (
    "attendance_percentage",
    "quiz_average_percentage",
    "assignment_average_percentage",
    "midterm_score_percentage",
    "current_avg_clo_attainment",
)

# CLAUDE.md section 9: at least 5 assessment records per student are required
# before a prediction is meaningful.
MIN_ASSESSMENT_RECORDS = 5

# Risk buckets over a 0-100 performance score. A lower score is higher risk.
HIGH_RISK_BELOW = 50.0
MEDIUM_RISK_BELOW = 70.0


def clamp_percentage(value: float) -> float:
    """Clamp any raw feature into the model's expected 0.0-100.0 range."""
    if value < 0.0:
        return 0.0
    if value > 100.0:
        return 100.0
    return float(value)


def assemble_feature_row(features: dict[str, float]) -> list[float]:
    """Turn a name->value mapping into the ordered, clamped feature vector.

    A missing feature defaults to 0.0 (the pessimistic end of the scale) rather
    than raising, so a student with, say, no recorded attendance still yields a
    usable row instead of crashing the batch.
    """
    return [clamp_percentage(features.get(name, 0.0)) for name in FEATURE_NAMES]


def risk_level_from_score(score: float) -> RiskLevel:
    """Bucket a 0-100 performance score into a risk level.

    Used both to synthesise training labels and as a deterministic fallback if
    the model is ever unavailable, so the two can never disagree on boundaries.
    """
    if score < HIGH_RISK_BELOW:
        return RiskLevel.high
    if score < MEDIUM_RISK_BELOW:
        return RiskLevel.medium
    return RiskLevel.low


def impact_label(shap_value: float) -> str:
    """Map a SHAP contribution (toward the high-risk class) to a human label.

    A positive value pushes the prediction toward higher risk; a negative one
    pulls it toward lower risk. Matches the `impact` field in CLAUDE.md
    section 9's SHAP schema.
    """
    return "increased_risk" if shap_value >= 0 else "decreased_risk"


def has_enough_records(assessment_record_count: int) -> bool:
    """Whether a student has the >=5 assessment records the model requires."""
    return assessment_record_count >= MIN_ASSESSMENT_RECORDS
