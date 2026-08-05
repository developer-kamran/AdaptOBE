from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (CheckConstraint("marks >= 0", name="ck_question_marks"),)

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
