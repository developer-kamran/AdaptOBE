from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.program import Program
from app.models.user import User, UserRole
from app.schemas.course import CourseCreate, CourseUpdate
from app.services.exceptions import ConflictError, NotFoundError, PermissionDeniedError


async def list_courses(
    db: AsyncSession, owner_faculty_id: int | None = None, current_user: User | None = None
) -> list[Course]:
    stmt = select(Course).order_by(Course.id)
    if owner_faculty_id is not None:
        stmt = stmt.where(Course.owner_faculty_id == owner_faculty_id)
    elif current_user is not None and current_user.role == UserRole.sub_admin:
        stmt = stmt.join(Program, Course.program_id == Program.id).where(
            Program.dept_id == current_user.dept_id
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_course(db: AsyncSession, course_id: int) -> Course:
    course = await db.get(Course, course_id)
    if course is None:
        raise NotFoundError(f"Course {course_id} not found")
    return course


async def ensure_can_manage(db: AsyncSession, course: Course, user: User) -> None:
    """Faculty manage only the courses they own; a sub_admin manages any
    course in their own department (via the course's programme)."""
    if user.role == UserRole.sub_admin:
        dept_id = (
            await db.execute(select(Program.dept_id).where(Program.id == course.program_id))
        ).scalar_one_or_none()
        if dept_id != user.dept_id:
            raise PermissionDeniedError("You do not have permission to manage this course")
        return

    if course.owner_faculty_id != user.id:
        raise PermissionDeniedError("You do not own this course")


async def get_course_for_user(db: AsyncSession, course_id: int, user: User) -> Course:
    course = await get_course(db, course_id)
    await ensure_can_manage(db, course, user)
    return course


async def create_course(db: AsyncSession, data: CourseCreate, owner: User) -> Course:
    if owner.role == UserRole.sub_admin:
        dept_id = (
            await db.execute(select(Program.dept_id).where(Program.id == data.program_id))
        ).scalar_one_or_none()
        if dept_id != owner.dept_id:
            raise PermissionDeniedError(
                "You do not have permission to create a course under this programme"
            )

    await _ensure_unique_offering(db, data.program_id, data.code, data.semester)

    course = Course(
        program_id=data.program_id,
        owner_faculty_id=owner.id,
        code=data.code,
        name=data.name,
        credit_hours=data.credit_hours,
        semester=data.semester,
    )
    db.add(course)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            "A course with this code already exists for this programme and semester"
        ) from exc

    await db.refresh(course)
    return course


async def _ensure_unique_offering(
    db: AsyncSession,
    program_id: int,
    code: str,
    semester: int,
    exclude_course_id: int | None = None,
) -> None:
    """Enforce the (program, code, semester) uniqueness rule ahead of the
    commit, so the error message can name the actual conflict rather than
    relying solely on the DB constraint (which still backstops races)."""
    stmt = select(Course).where(
        Course.program_id == program_id,
        Course.code == code,
        Course.semester == semester,
    )
    if exclude_course_id is not None:
        stmt = stmt.where(Course.id != exclude_course_id)

    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            "A course with this code already exists for this programme and semester"
        )


async def update_course(
    db: AsyncSession, course_id: int, data: CourseUpdate, user: User
) -> Course:
    course = await get_course_for_user(db, course_id, user)
    changes = data.model_dump(exclude_unset=True)

    # A PATCH may touch just one of program/code/semester -- re-check the
    # *resulting* combination (existing values merged with the patch), not
    # just the fields that changed.
    if {"program_id", "code", "semester"} & changes.keys():
        await _ensure_unique_offering(
            db,
            changes.get("program_id", course.program_id),
            changes.get("code", course.code),
            changes.get("semester", course.semester),
            exclude_course_id=course.id,
        )

    for field, value in changes.items():
        setattr(course, field, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            "A course with this code already exists for this programme and semester"
        ) from exc

    await db.refresh(course)
    return course


async def delete_course(db: AsyncSession, course_id: int, user: User) -> None:
    course = await get_course_for_user(db, course_id, user)
    await db.delete(course)
    await db.commit()
