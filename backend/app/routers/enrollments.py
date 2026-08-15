from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.enrollment import EnrollmentCreate, EnrollmentRead
from app.schemas.enrollment_import import ConfirmEnrollImportRequest, EnrollImportPreview
from app.services import attainment_service, course_service, enrollment_import_service, enrollment_service, file_parsers
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/api/v1/courses", tags=["enrollments"])

# Enrollment is a faculty-operational concern -- neither admin tier touches
# it, per the admin-hierarchy redesign.
FacultyOnly = Depends(require_roles(UserRole.faculty))

#: Rosters are small. This mostly exists to stop a huge upload from being
#: parsed into memory (mirrors student_import.py's limit).
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


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
    current_user: User = FacultyOnly,
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
    current_user: User = FacultyOnly,
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
    current_user: User = FacultyOnly,
):
    try:
        await enrollment_service.unenroll_student(db, course_id, student_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    await attainment_service.recalculate_course_attainment(db, course_id)


@router.post("/{course_id}/enrollments/import/preview", response_model=EnrollImportPreview)
async def preview_enrollment_import(
    course_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    """Parse an uploaded roster and classify each row against existing
    student accounts. Enrolls nothing."""
    try:
        course = await course_service.get_course_for_user(db, course_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    filename = file.filename or ""
    if not filename.lower().endswith(file_parsers.SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Unsupported file type. Upload one of: "
                f"{', '.join(file_parsers.SUPPORTED_EXTENSIONS)}"
            ),
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large (limit {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The file is empty"
        )

    try:
        return await enrollment_import_service.build_preview(db, course, content, filename)
    except file_parsers.FileParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.post(
    "/{course_id}/enrollments/import/confirm",
    response_model=list[EnrollmentRead],
    status_code=status.HTTP_201_CREATED,
)
async def confirm_enrollment_import(
    course_id: int,
    data: ConfirmEnrollImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    """Enroll the confirmed (already-matched, already-eligible) student ids.
    Re-uses the same enrollment path as manual enrollment -- no separate
    "import enroll" logic to keep in sync."""
    try:
        enrollments = await enrollment_service.enroll_students(
            db, course_id, data.student_ids, current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc

    await attainment_service.recalculate_course_attainment(db, course_id)
    return enrollments
