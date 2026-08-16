from sqlalchemy import CheckConstraint, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AttendanceRecord(Base):
    """A student's attendance percentage for one course.

    Module 5 needs `attendance_percentage` as an XGBoost feature but no
    attendance data existed anywhere in the schema. Rather than model every
    class session (out of scope for this project), attendance is stored as a
    single faculty-entered percentage per (course, student) -- exactly the
    granularity the feature vector consumes. Faculty maintain it from the
    course page; it is never derived from scores.
    """

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("course_id", "student_id", name="uq_attendance_course_student"),
        CheckConstraint(
            "attendance_percentage >= 0 AND attendance_percentage <= 100",
            name="ck_attendance_percentage_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    attendance_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
