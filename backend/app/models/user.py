import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, enum.Enum):
    # NOTE: the Postgres enum type `user_role` also still carries a legacy
    # `admin` label (see migration d1a4c9f2e6b7) from before the super_admin /
    # sub_admin split. It's intentionally left in place at the DB level --
    # dropping a Postgres enum label requires a full type rebuild -- but no
    # code should ever assign or compare against it again.
    super_admin = "super_admin"
    sub_admin = "sub_admin"
    faculty = "faculty"
    student = "student"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    enrollment_no: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    seat_no: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Null for super_admin (institution-wide). Required for sub_admin, faculty,
    # and student -- enforced in schemas/services, not a DB NOT NULL, since the
    # column is shared across roles that do and don't need it.
    dept_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    # Required for sub_admin and faculty (labeled "Employee ID" / "Faculty ID"
    # respectively in the UI, same underlying column) -- enforced in
    # schemas/services, same nullable-unique pattern as enrollment_no/seat_no.
    employee_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    # Required for student -- enforced in schemas/services.
    father_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Fernet-encrypted copy of the password set at creation time, so an
    # authorized admin can view it later from the Edit page. Login never
    # reads this column -- password_hash (bcrypt, one-way) is the sole
    # source of truth for authentication. NULL for any account whose
    # password was set outside app code (e.g. scripts/seed_admin.py, or a
    # password changed directly in the database).
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
