from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.institution import expected_seat_no_prefix, is_backlog_batch_year
from app.core.security import decrypt_password
from app.models.course import Course
from app.models.program import Program
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.services import auth_service
from app.services.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.id))
    return list(result.scalars().all())


async def list_users_for_admin(db: AsyncSession, current_user: User) -> list[User]:
    """Super admins manage sub-admins only; sub-admins manage their own
    department's faculty/students only. Mirrors ensure_can_manage_user."""
    if current_user.role == UserRole.super_admin:
        stmt = select(User).where(User.role == UserRole.sub_admin).order_by(User.id)
    elif current_user.role == UserRole.sub_admin:
        stmt = (
            select(User)
            .where(
                User.role.in_([UserRole.faculty, UserRole.student]),
                User.dept_id == current_user.dept_id,
            )
            .order_by(User.id)
        )
    else:
        raise PermissionDeniedError("You do not have permission to list users")

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_active_students(
    db: AsyncSession,
    current_user: User | None = None,
    course_id: int | None = None,
    backlog: bool = False,
) -> list[User]:
    """Faculty/sub-admins need this to pick students for enrollment, but the
    full user directory (`list_users`) is admin-tier-only -- this is a
    narrower, safe subset. Both sub-admins and faculty only see their own
    department's students (faculty have a `dept_id` too, same as sub-admins).

    `course_id`, when given, further narrows the list based on the course's
    own programme and semester -- see `app.core.institution`:
      * `backlog=False` (default, normal enrollment): only students whose
        seat number matches the *current-batch* prefix for that course's
        programme and semester right now (`expected_seat_no_prefix`) --
        e.g. a BSSE course in semester 4 during 2026 only offers students
        who enrolled in 2024. A programme with no configured seat-number
        code is not filtered.
      * `backlog=True` ("Add Backlog Student"): any department student (any
        programme) whose seat number encodes an *earlier* enrollment year
        than the current batch for that semester (`is_backlog_batch_year`)
        -- a student repeating the course from an earlier cohort. Students
        whose seat number doesn't parse are excluded, since eligibility
        can't be confirmed either way.
    Omit `course_id` entirely to search the whole (department-scoped) roster
    unfiltered."""
    stmt = select(User).where(User.role == UserRole.student, User.is_active.is_(True))
    if current_user is not None and current_user.role in (UserRole.sub_admin, UserRole.faculty):
        stmt = stmt.where(User.dept_id == current_user.dept_id)

    course: Course | None = None
    if course_id is not None:
        course = await db.get(Course, course_id)

    if course is not None and not backlog:
        program_code = (
            await db.execute(select(Program.code).where(Program.id == course.program_id))
        ).scalar_one_or_none()
        prefix = expected_seat_no_prefix(program_code, course.semester) if program_code else None
        if prefix:
            stmt = stmt.where(User.seat_no.like(f"{prefix}%"))

    result = await db.execute(stmt.order_by(User.full_name))
    students = list(result.scalars().all())

    if course is not None and backlog:
        students = [s for s in students if is_backlog_batch_year(s.seat_no, course.semester)]

    return students


async def get_user(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user


def ensure_can_manage_user(current_user: User, target_user: User) -> None:
    """Mirrors course_service.ensure_can_manage: super_admin may only act on
    sub_admin accounts; sub_admin may only act on faculty/student accounts in
    their own department. Anything else is a 403, including changing IDs in
    the URL to reach another department's or tier's accounts."""
    if current_user.role == UserRole.super_admin:
        if target_user.role != UserRole.sub_admin:
            raise PermissionDeniedError("You do not have permission to manage this user")
        return

    if current_user.role == UserRole.sub_admin:
        if target_user.role not in (UserRole.faculty, UserRole.student):
            raise PermissionDeniedError("You do not have permission to manage this user")
        if target_user.dept_id != current_user.dept_id:
            raise PermissionDeniedError("You do not have permission to manage this user")
        return

    raise PermissionDeniedError("You do not have permission to manage this user")


async def get_user_scoped(db: AsyncSession, user_id: int, current_user: User) -> User:
    user = await get_user(db, user_id)
    ensure_can_manage_user(current_user, user)
    return user


async def get_user_password(db: AsyncSession, user_id: int, current_user: User) -> str | None:
    """Reuses the exact same scope check as every other per-user action --
    a sub_admin can only reveal passwords for their own department's
    faculty/student, a super_admin only for sub_admin accounts. Returns
    None (not a 404) when the account predates this feature or had its
    password set outside app code, so the caller can render "not available"
    instead of erroring."""
    user = await get_user_scoped(db, user_id, current_user)
    if user.password_encrypted is None:
        return None
    return decrypt_password(user.password_encrypted)


async def create_user_scoped(db: AsyncSession, data: UserCreate, current_user: User) -> User:
    """Enforces the creation matrix: a super_admin may only create sub_admin
    accounts (picking the target department explicitly); a sub_admin may
    only create faculty/student accounts, always in their own department
    regardless of what dept_id was submitted -- this is what stops a
    sub-admin from planting an account in another department by editing the
    request body."""
    if current_user.role == UserRole.super_admin:
        if data.role != UserRole.sub_admin:
            raise ValidationError("Super admins can only create sub_admin accounts")
    elif current_user.role == UserRole.sub_admin:
        if data.role not in (UserRole.faculty, UserRole.student):
            raise ValidationError("Sub-admins can only create faculty or student accounts")
        data = data.model_copy(update={"dept_id": current_user.dept_id})
    else:
        raise PermissionDeniedError("You do not have permission to create users")

    return await auth_service.register_user(db, data)


async def _check_uniqueness(db: AsyncSession, user_id: int, data: UserUpdate) -> None:
    conditions = []
    if data.email is not None:
        conditions.append(User.email == data.email)
    if data.enrollment_no is not None:
        conditions.append(User.enrollment_no == data.enrollment_no)
    if data.seat_no is not None:
        conditions.append(User.seat_no == data.seat_no)
    if data.employee_id is not None:
        conditions.append(User.employee_id == data.employee_id)
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
    if data.employee_id is not None and existing.employee_id == data.employee_id:
        raise ConflictError("A user with this employee ID already exists")


def _reject_privilege_escalation(current_user: User, target_user: User, data: UserUpdate) -> None:
    """A PATCH must not be usable to change a user's role/department out of
    the caller's manageable scope -- e.g. a sub_admin promoting a student to
    sub_admin, or moving them to a different department."""
    if data.role is not None and data.role != target_user.role:
        raise PermissionDeniedError("You do not have permission to change this user's role")

    if current_user.role == UserRole.sub_admin and data.dept_id is not None:
        if data.dept_id != current_user.dept_id:
            raise PermissionDeniedError(
                "You do not have permission to move this user to another department"
            )


async def update_user(
    db: AsyncSession, user_id: int, data: UserUpdate, current_user: User
) -> User:
    user = await get_user(db, user_id)
    ensure_can_manage_user(current_user, user)
    _reject_privilege_escalation(current_user, user, data)
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


async def deactivate_user(db: AsyncSession, user_id: int, current_user: User) -> User:
    user = await get_user(db, user_id)
    ensure_can_manage_user(current_user, user)
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user
