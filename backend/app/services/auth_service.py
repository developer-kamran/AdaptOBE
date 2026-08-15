from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_password, generate_password, hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.exceptions import ConflictError


async def _check_uniqueness(db: AsyncSession, data: UserCreate) -> None:
    conditions = [User.email == data.email]
    if data.enrollment_no is not None:
        conditions.append(User.enrollment_no == data.enrollment_no)
    if data.seat_no is not None:
        conditions.append(User.seat_no == data.seat_no)
    if data.employee_id is not None:
        conditions.append(User.employee_id == data.employee_id)

    result = await db.execute(select(User).where(or_(*conditions)))
    existing = result.scalars().first()
    if existing is None:
        return

    if existing.email == data.email:
        raise ConflictError("A user with this email already exists")
    if data.enrollment_no is not None and existing.enrollment_no == data.enrollment_no:
        raise ConflictError("A user with this enrollment number already exists")
    if data.seat_no is not None and existing.seat_no == data.seat_no:
        raise ConflictError("A user with this seat number already exists")
    if data.employee_id is not None and existing.employee_id == data.employee_id:
        raise ConflictError("A user with this employee ID already exists")


async def register_user(db: AsyncSession, data: UserCreate) -> User:
    await _check_uniqueness(db, data)

    # No human picks a password for an account created on someone else's
    # behalf (e.g. the manual "Add Student" form) -- generate one with the
    # same criteria bulk import already uses, and let the caller reveal it
    # via GET /admin/users/{id}/password afterward.
    password = data.password or generate_password()

    user = User(
        email=data.email,
        password_hash=hash_password(password),
        password_encrypted=encrypt_password(password),
        full_name=data.full_name,
        role=data.role,
        enrollment_no=data.enrollment_no,
        seat_no=data.seat_no,
        father_name=data.father_name,
        dept_id=data.dept_id,
        employee_id=data.employee_id,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A user with these details already exists") from exc

    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None

    return user
