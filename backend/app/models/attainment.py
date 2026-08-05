from sqlalchemy import Boolean, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AttainmentRecord(Base):
    __tablename__ = "attainment_records"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "clo_id", name="uq_attainment_scope"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    clo_id: Mapped[int] = mapped_column(ForeignKey("clos.id", ondelete="CASCADE"), nullable=False)
    attainment_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_achieved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
