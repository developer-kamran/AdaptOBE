from sqlalchemy import CheckConstraint, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StudentScore(Base):
    __tablename__ = "student_scores"
    __table_args__ = (
        UniqueConstraint("question_id", "student_id", name="uq_question_student"),
        CheckConstraint("marks_obtained >= 0", name="ck_score_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    marks_obtained: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
