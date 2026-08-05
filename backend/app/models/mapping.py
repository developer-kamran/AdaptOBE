from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CloPloMapping(Base):
    __tablename__ = "clo_plo_mappings"
    __table_args__ = (
        UniqueConstraint("clo_id", "plo_id", name="uq_clo_plo"),
        CheckConstraint("strength BETWEEN 1 AND 3", name="ck_mapping_strength"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    clo_id: Mapped[int] = mapped_column(
        ForeignKey("clos.id", ondelete="CASCADE"), nullable=False
    )
    plo_id: Mapped[int] = mapped_column(
        ForeignKey("plos.id", ondelete="CASCADE"), nullable=False
    )
    strength: Mapped[int] = mapped_column(Integer, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
