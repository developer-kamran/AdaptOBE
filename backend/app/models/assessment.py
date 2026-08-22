import enum
from datetime import date as date_type

import sqlalchemy as sa
from sqlalchemy import Date, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssessmentType(str, enum.Enum):
    quiz = "quiz"
    assignment = "assignment"
    lab = "lab"
    project = "project"
    midterm = "midterm"
    final = "final"


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[AssessmentType] = mapped_column(
        Enum(AssessmentType, name="assessment_type"), nullable=False
    )
    total_marks: Mapped[float] = mapped_column(Float, nullable=False)
    weightage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    # "Allocated Time" on the exported exam paper (Feature: export to PDF/Word).
    # Nullable -- most existing assessments predate this field and have no
    # duration to show.
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        sa.CheckConstraint("total_marks > 0", name="ck_assessment_total_marks"),
        sa.CheckConstraint(
            "weightage_percent >= 0 AND weightage_percent <= 100",
            name="ck_assessment_weightage",
        ),
        sa.CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes > 0",
            name="ck_assessment_duration_minutes",
        ),
    )
