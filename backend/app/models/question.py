import enum

from sqlalchemy import CheckConstraint, Enum, Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QuestionType(str, enum.Enum):
    question = "question"
    mcq = "mcq"
    fill_blank = "fill_blank"
    true_false = "true_false"
    project = "project"
    lab = "lab"


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("marks > 0", name="ck_question_marks"),
        # A question number identifies a question within its own assessment
        # only -- two different assessments may both have a "Q1".
        UniqueConstraint(
            "assessment_id", "question_number", name="uq_question_assessment_number"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    marks: Mapped[float] = mapped_column(Float, nullable=False)
    # Deleting a CLO untags its questions rather than destroying exam records.
    clo_id: Mapped[int | None] = mapped_column(
        ForeignKey("clos.id", ondelete="SET NULL"), nullable=True
    )
    # Question wording, used by the AI tagging suggestion in app/ml.
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type"),
        nullable=False,
        default=QuestionType.question,
        server_default=QuestionType.question.value,
    )
    # Type-specific payload (MCQ options, fill-in-the-blank answer, project/lab
    # description, ...) -- see schemas/question.py for the shape per type.
    # Kept as a flexible JSONB column, same idiom CLAUDE.md already specifies
    # for `student_predictions.shap_explanation`, rather than a table per type.
    type_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
