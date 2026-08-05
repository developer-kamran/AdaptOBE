from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.enrollment import EnrollmentCreate, EnrollmentRead
from app.services import attainment_service, course_service, enrollment_service
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/api/v1/courses", tags=["enrollments"])

FacultyOrAdmin = Depends(require_roles(UserRole.faculty, UserRole.admin))


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
    )


@router.get("/{course_id}/enrollments", response_model=list[EnrollmentRead])
async def list_enrollments(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        await course_service.get_course_for_user(db, course_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    return await enrollment_service.list_enrollments(db, course_id)


@router.post(
    "/{course_id}/enrollments",
    response_model=list[EnrollmentRead],
    status_code=status.HTTP_201_CREATED,
)
async def enroll_students(
    course_id: int,
    data: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        enrollments = await enrollment_service.enroll_students(
            db, course_id, data.student_ids, current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc

    # New students join the cohort, which moves every class average.
    await attainment_service.recalculate_course_attainment(db, course_id)
    return enrollments


@router.delete(
    "/{course_id}/enrollments/{student_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def unenroll_student(
    course_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        await enrollment_service.unenroll_student(db, course_id, student_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    await attainment_service.recalculate_course_attainment(db, course_id)
