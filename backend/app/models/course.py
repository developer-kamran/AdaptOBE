from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

DEFAULT_ATTAINMENT_THRESHOLD = 50.0


class Course(Base):
    __tablename__ = "courses"
    # A course offering is unique per (programme, code, semester) -- the same
    # code may legitimately be reused in a different programme or a different
    # semester (e.g. a repeated/retake offering), so uniqueness is NOT global
    # on `code` alone.
    __table_args__ = (
        UniqueConstraint(
            "program_id", "code", "semester", name="uq_course_program_code_semester"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False)
    owner_faculty_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    credit_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    # Class-average CLO attainment must reach this to count as achieved (section 8).
    attainment_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=DEFAULT_ATTAINMENT_THRESHOLD,
        server_default=str(DEFAULT_ATTAINMENT_THRESHOLD),
    )
