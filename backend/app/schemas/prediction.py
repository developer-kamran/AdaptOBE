from pydantic import BaseModel, ConfigDict

from app.models.prediction import RiskLevel


class FeatureContribution(BaseModel):
    """One feature's SHAP contribution (CLAUDE.md section 9)."""

    feature: str
    value: float
    shap_value: float
    impact: str


class ShapExplanation(BaseModel):
    """The exact SHAP payload shape from CLAUDE.md section 9."""

    base_value: float
    predicted_risk: str
    confidence: float
    feature_contributions: list[FeatureContribution]


class StudentRiskPrediction(BaseModel):
    student_id: int
    full_name: str
    seat_no: str | None
    risk_level: RiskLevel
    confidence_score: float
    predicted_score: float
    features: dict[str, float]
    shap_explanation: ShapExplanation


class SkippedStudent(BaseModel):
    """A student excluded from prediction, with why (e.g. too few records)."""

    student_id: int
    full_name: str
    seat_no: str | None
    reason: str
    assessment_records: int


class LearningGapCLO(BaseModel):
    """A CLO whose class-average attainment is below the course threshold."""

    clo_id: int
    code: str
    title: str
    class_average: float
    threshold: float


class RiskPredictionReport(BaseModel):
    course_id: int
    threshold: float
    predicted_count: int
    predictions: list[StudentRiskPrediction]
    skipped: list[SkippedStudent]
    learning_gaps: list[LearningGapCLO]


class StoredPrediction(BaseModel):
    """A persisted prediction row (from GET), without re-running the model."""

    model_config = ConfigDict(from_attributes=True)

    student_id: int
    course_id: int
    risk_level: RiskLevel
    confidence_score: float
    predicted_score: float
    shap_explanation: ShapExplanation


class StoredPredictionReport(BaseModel):
    course_id: int
    threshold: float
    predictions: list[StoredPrediction]
    learning_gaps: list[LearningGapCLO]
