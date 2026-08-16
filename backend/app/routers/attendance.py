from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceRead,
    BulkAttendanceRequest,
    BulkAttendanceResponse,
)
from app.services import attendance_service
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/api/v1/courses", tags=["attendance"])

# Attendance feeds the risk model and is a faculty-operational concern, so it
# follows the same faculty-only rule as scoring and attainment.
FacultyOnly = Depends(require_roles(UserRole.faculty))


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))


@router.get("/{course_id}/attendance", response_model=list[AttendanceRead])
async def list_attendance(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        from app.services import course_service

        await course_service.get_course_for_user(db, course_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc
    return await attendance_service.list_attendance(db, course_id)


@router.post("/{course_id}/attendance", response_model=BulkAttendanceResponse)
async def set_attendance(
    course_id: int,
    data: BulkAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        saved = await attendance_service.bulk_set_attendance(db, course_id, data, current_user)
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc
    return BulkAttendanceResponse(saved=saved)
