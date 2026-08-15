from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.plo import PLOCreate, PLORead, PLOUpdate
from app.services import plo_service
from app.services.exceptions import ConflictError, NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api/v1/admin/plos", tags=["admin-plos"])

# PLOs are department-level setup, owned by that department's sub_admin. But
# faculty need to *read* PLOs to confirm CLO-PLO mappings on their own courses
# -- without this, the mapping UI could never show a faculty user what a PLO
# actually says.
FacultyOrSubAdmin = Depends(require_roles(UserRole.faculty, UserRole.sub_admin))
SubAdminOnly = Depends(require_roles(UserRole.sub_admin))


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    raise AssertionError(f"unhandled exception type: {type(exc)}")


@router.get("", response_model=list[PLORead])
async def list_plos(
    program_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    return await plo_service.list_plos(db, program_id, current_user)


@router.post("", response_model=PLORead, status_code=status.HTTP_201_CREATED)
async def create_plo(
    data: PLOCreate, db: AsyncSession = Depends(get_db), current_user: User = SubAdminOnly
):
    try:
        return await plo_service.create_plo(db, data, current_user)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise _translate(exc) from exc


@router.get("/{plo_id}", response_model=PLORead)
async def get_plo(
    plo_id: int, db: AsyncSession = Depends(get_db), current_user: User = FacultyOrSubAdmin
):
    try:
        if current_user.role == UserRole.sub_admin:
            return await plo_service.get_plo_scoped(db, plo_id, current_user)
        return await plo_service.get_plo(db, plo_id)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc


@router.patch("/{plo_id}", response_model=PLORead)
async def update_plo(
    plo_id: int, data: PLOUpdate, db: AsyncSession = Depends(get_db), current_user: User = SubAdminOnly
):
    try:
        return await plo_service.update_plo(db, plo_id, data, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc


@router.delete("/{plo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plo(
    plo_id: int, db: AsyncSession = Depends(get_db), current_user: User = SubAdminOnly
):
    try:
        await plo_service.delete_plo(db, plo_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc
