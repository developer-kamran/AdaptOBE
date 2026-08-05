from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.attainment import CourseAttainmentReport, StudentProgressReport
from app.services import attainment_service, course_service
from app.services.exceptions import NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api/v1/attainment", tags=["attainment"])

FacultyOrAdmin = Depends(require_roles(UserRole.faculty, UserRole.admin))


@router.get("/course/{course_id}", response_model=CourseAttainmentReport)
async def course_attainment(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        await course_service.get_course_for_user(db, course_id, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return await attainment_service.build_course_report(db, course_id)


@router.post("/course/{course_id}/recalculate", response_model=CourseAttainmentReport)
async def recalculate(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        await course_service.get_course_for_user(db, course_id, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    await attainment_service.recalculate_course_attainment(db, course_id)
    return await attainment_service.build_course_report(db, course_id)


@router.get(
    "/course/{course_id}/student/{student_id}", response_model=StudentProgressReport
)
async def student_attainment(
    course_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        await course_service.get_course_for_user(db, course_id, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return await attainment_service.build_student_report(db, course_id, student_id)
