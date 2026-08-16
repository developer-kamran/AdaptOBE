import enum

from sqlalchemy import Enum, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class StudentPrediction(Base):
    """XGBoost risk prediction for one student in one course (CLAUDE.md section 6/9).

    Like `attainment_records`, these are derived data: the risk service wipes a
    course's rows and re-inserts them on every prediction run rather than
    patching in place, so the table can never drift from the model's latest
    output. `shap_explanation` stores the exact SHAP payload shape from
    CLAUDE.md section 9 as JSONB.
    """

    __tablename__ = "student_predictions"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_prediction_student_course"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level"), nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_score: Mapped[float] = mapped_column(Float, nullable=False)
    shap_explanation: Mapped[dict] = mapped_column(JSONB, nullable=False)
