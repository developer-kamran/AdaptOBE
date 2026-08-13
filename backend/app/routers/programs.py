from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.program import ProgramCreate, ProgramRead, ProgramUpdate
from app.services import program_service
from app.services.exceptions import ConflictError, NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api/v1/admin/programs", tags=["admin-programs"])

# Programmes are department-level setup, owned by that department's sub_admin.
# Faculty still need to *read* the programme list to pick one when creating a
# course -- without this, course creation would be broken for faculty users.
FacultyOrSubAdmin = Depends(require_roles(UserRole.faculty, UserRole.sub_admin))
SubAdminOnly = Depends(require_roles(UserRole.sub_admin))


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    raise AssertionError(f"unhandled exception type: {type(exc)}")


@router.get("", response_model=list[ProgramRead])
async def list_programs(
    db: AsyncSession = Depends(get_db), current_user: User = FacultyOrSubAdmin
):
    return await program_service.list_programs(db, current_user)


@router.post("", response_model=ProgramRead, status_code=status.HTTP_201_CREATED)
async def create_program(
    data: ProgramCreate, db: AsyncSession = Depends(get_db), current_user: User = SubAdminOnly
):
    try:
        return await program_service.create_program(db, data, current_user)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{program_id}", response_model=ProgramRead)
async def get_program(
    program_id: int, db: AsyncSession = Depends(get_db), current_user: User = FacultyOrSubAdmin
):
    try:
        if current_user.role == UserRole.sub_admin:
            return await program_service.get_program_scoped(db, program_id, current_user)
        return await program_service.get_program(db, program_id)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc


@router.patch("/{program_id}", response_model=ProgramRead)
async def update_program(
    program_id: int,
    data: ProgramUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = SubAdminOnly,
):
    try:
        return await program_service.update_program(db, program_id, data, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_program(
    program_id: int, db: AsyncSession = Depends(get_db), current_user: User = SubAdminOnly
):
    try:
        await program_service.delete_program(db, program_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc
