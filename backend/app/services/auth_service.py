from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.exceptions import ConflictError


async def _check_uniqueness(db: AsyncSession, data: UserCreate) -> None:
    conditions = [User.email == data.email]
    if data.enrollment_no is not None:
        conditions.append(User.enrollment_no == data.enrollment_no)
    if data.seat_no is not None:
        conditions.append(User.seat_no == data.seat_no)

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


async def register_user(db: AsyncSession, data: UserCreate) -> User:
    await _check_uniqueness(db, data)

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        enrollment_no=data.enrollment_no,
        seat_no=data.seat_no,
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
