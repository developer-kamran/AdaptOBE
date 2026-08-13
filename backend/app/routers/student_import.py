from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.student_import import ConfirmImportRequest, ImportPreview, ImportResult
from app.services import file_parsers, student_import_service
from app.services.exceptions import PermissionDeniedError, ValidationError

router = APIRouter(prefix="/api/v1/admin/students", tags=["student-import"])

# Importing students is department-scoped roster management, which is a
# sub_admin's job -- a super_admin manages departments and sub-admins only.
SubAdminOnly = Depends(require_roles(UserRole.sub_admin))

#: Rosters are small. This mostly exists to stop a huge upload from being
#: parsed into memory.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.post("/import/preview", response_model=ImportPreview)
async def preview_student_import(
    file: UploadFile = File(...),
    _current_user: User = SubAdminOnly,
):
    """Parse an uploaded roster and report what was found. Creates nothing."""
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
        return await student_import_service.build_preview(content, filename)
    except file_parsers.FileParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.post("/import/confirm", response_model=ImportResult)
async def confirm_student_import(
    data: ConfirmImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = SubAdminOnly,
):
    """Create accounts for the confirmed rows.

    The payload is re-validated by `ConfirmStudent` (every required field
    non-empty, email well-formed) -- the browser having decided a row was
    complete is not taken on trust.
    """
    try:
        return await student_import_service.commit_students(db, data.students, current_user)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
