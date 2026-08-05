from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    dept_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    # Short institutional code, e.g. BSSE / BSCS / BSAI / BSDS.
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_semesters: Mapped[int] = mapped_column(Integer, nullable=False)
