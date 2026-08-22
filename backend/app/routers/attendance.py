from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceRead,
    BulkAttendanceRequest,
    BulkAttendanceResponse,
)
from app.schemas.attendance_import import AttendanceImportPreview, ConfirmAttendanceImportRequest
from app.services import attendance_import_service, attendance_service, course_service, file_parsers
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/api/v1/courses", tags=["attendance"])

# Attendance feeds the risk model and is a faculty-operational concern, so it
# follows the same faculty-only rule as scoring and attainment.
FacultyOnly = Depends(require_roles(UserRole.faculty))

#: Attendance sheets are small. Mirrors enrollments.py's import upload cap.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


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


@router.post("/{course_id}/attendance/import/preview", response_model=AttendanceImportPreview)
async def preview_attendance_import(
    course_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    """Parse an uploaded attendance sheet and classify each row against this
    course's enrolled roster. Saves nothing."""
    try:
        course = await course_service.get_course_for_user(db, course_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    filename = file.filename or ""
    if not filename.lower().endswith(file_parsers.SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported file type. Upload one of: {', '.join(file_parsers.SUPPORTED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large (limit {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The file is empty")

    try:
        return await attendance_import_service.build_preview(db, course, content, filename)
    except file_parsers.FileParseError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/{course_id}/attendance/import/confirm", response_model=BulkAttendanceResponse)
async def confirm_attendance_import(
    course_id: int,
    data: ConfirmAttendanceImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    """Delegates to the same `bulk_set_attendance` the manual Attendance
    panel uses -- no parallel write path."""
    try:
        saved = await attendance_service.bulk_set_attendance(
            db, course_id, BulkAttendanceRequest(entries=data.entries), current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc
    return BulkAttendanceResponse(saved=saved)
