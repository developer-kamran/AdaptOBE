from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import CourseEnrollment
from app.models.user import User, UserRole
from app.services import course_service
from app.services.exceptions import NotFoundError, ValidationError


async def list_enrollments(db: AsyncSession, course_id: int) -> list[CourseEnrollment]:
    result = await db.execute(
        select(CourseEnrollment)
        .where(CourseEnrollment.course_id == course_id)
        .order_by(CourseEnrollment.id)
    )
    return list(result.scalars().all())


async def list_enrolled_student_ids(db: AsyncSession, course_id: int) -> list[int]:
    result = await db.execute(
        select(CourseEnrollment.student_id)
        .where(CourseEnrollment.course_id == course_id)
        .order_by(CourseEnrollment.student_id)
    )
    return list(result.scalars().all())


async def enroll_students(
    db: AsyncSession, course_id: int, student_ids: list[int], user: User
) -> list[CourseEnrollment]:
    await course_service.get_course_for_user(db, course_id, user)

    for student_id in student_ids:
        student = await db.get(User, student_id)
        if student is None:
            raise NotFoundError(f"User {student_id} not found")
        if student.role != UserRole.student:
            raise ValidationError(f"User {student_id} is not a student")

    existing = set(await list_enrolled_student_ids(db, course_id))
    for student_id in student_ids:
        if student_id not in existing:
            db.add(CourseEnrollment(course_id=course_id, student_id=student_id))

    await db.commit()
    return await list_enrollments(db, course_id)


async def unenroll_student(db: AsyncSession, course_id: int, student_id: int, user: User) -> None:
    await course_service.get_course_for_user(db, course_id, user)

    result = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if enrollment is None:
        raise NotFoundError(f"Student {student_id} is not enrolled in course {course_id}")

    await db.delete(enrollment)
    await db.commit()
