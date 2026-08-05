from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.schemas.user import UserUpdate
from app.services.exceptions import ConflictError, NotFoundError


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.id))
    return list(result.scalars().all())


async def list_active_students(db: AsyncSession) -> list[User]:
    """Faculty need this to pick students for enrollment, but the full user
    directory (`list_users`) is admin-only -- this is a narrower, safe subset."""
    result = await db.execute(
        select(User)
        .where(User.role == UserRole.student, User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return list(result.scalars().all())


async def get_user(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user


async def _check_uniqueness(db: AsyncSession, user_id: int, data: UserUpdate) -> None:
    conditions = []
    if data.email is not None:
        conditions.append(User.email == data.email)
    if data.enrollment_no is not None:
        conditions.append(User.enrollment_no == data.enrollment_no)
    if data.seat_no is not None:
        conditions.append(User.seat_no == data.seat_no)
    if not conditions:
        return

    result = await db.execute(select(User).where(or_(*conditions), User.id != user_id))
    existing = result.scalars().first()
    if existing is None:
        return

    if data.email is not None and existing.email == data.email:
        raise ConflictError("A user with this email already exists")
    if data.enrollment_no is not None and existing.enrollment_no == data.enrollment_no:
        raise ConflictError("A user with this enrollment number already exists")
    if data.seat_no is not None and existing.seat_no == data.seat_no:
        raise ConflictError("A user with this seat number already exists")


async def update_user(db: AsyncSession, user_id: int, data: UserUpdate) -> User:
    user = await get_user(db, user_id)
    await _check_uniqueness(db, user_id, data)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A user with these details already exists") from exc

    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user_id: int) -> User:
    user = await get_user(db, user_id)
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user
