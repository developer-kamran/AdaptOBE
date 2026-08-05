from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.user import User, UserRole
from app.schemas.course import CourseCreate, CourseUpdate
from app.services.exceptions import ConflictError, NotFoundError, PermissionDeniedError


async def list_courses(db: AsyncSession, owner_faculty_id: int | None = None) -> list[Course]:
    stmt = select(Course).order_by(Course.id)
    if owner_faculty_id is not None:
        stmt = stmt.where(Course.owner_faculty_id == owner_faculty_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_course(db: AsyncSession, course_id: int) -> Course:
    course = await db.get(Course, course_id)
    if course is None:
        raise NotFoundError(f"Course {course_id} not found")
    return course


def ensure_can_manage(course: Course, user: User) -> None:
    """Admins manage any course; faculty only the ones they own."""
    if user.role == UserRole.admin:
        return
    if course.owner_faculty_id != user.id:
        raise PermissionDeniedError("You do not own this course")


async def get_course_for_user(db: AsyncSession, course_id: int, user: User) -> Course:
    course = await get_course(db, course_id)
    ensure_can_manage(course, user)
    return course


async def create_course(db: AsyncSession, data: CourseCreate, owner: User) -> Course:
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
            "A course with this code already exists, or the program reference is invalid"
        ) from exc

    await db.refresh(course)
    return course


async def update_course(
    db: AsyncSession, course_id: int, data: CourseUpdate, user: User
) -> Course:
    course = await get_course_for_user(db, course_id, user)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(course, field, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            "A course with this code already exists, or the program reference is invalid"
        ) from exc

    await db.refresh(course)
    return course


async def delete_course(db: AsyncSession, course_id: int, user: User) -> None:
    course = await get_course_for_user(db, course_id, user)
    await db.delete(course)
    await db.commit()
