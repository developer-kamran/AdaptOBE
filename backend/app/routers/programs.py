from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import UserRole
from app.schemas.program import ProgramCreate, ProgramRead, ProgramUpdate
from app.services import program_service
from app.services.exceptions import ConflictError, NotFoundError

router = APIRouter(prefix="/api/v1/admin/programs", tags=["admin-programs"])

# Programmes are institutional setup, so only admins create/edit/delete them.
# But faculty need to *read* the programme list to pick one when creating a
# course -- without this, course creation would be broken for faculty users.
FacultyOrAdmin = Depends(require_roles(UserRole.faculty, UserRole.admin))
AdminOnly = Depends(require_roles(UserRole.admin))


@router.get("", response_model=list[ProgramRead])
async def list_programs(db: AsyncSession = Depends(get_db), _=FacultyOrAdmin):
    return await program_service.list_programs(db)


@router.post("", response_model=ProgramRead, status_code=status.HTTP_201_CREATED)
async def create_program(data: ProgramCreate, db: AsyncSession = Depends(get_db), _=AdminOnly):
    try:
        return await program_service.create_program(db, data)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{program_id}", response_model=ProgramRead)
async def get_program(program_id: int, db: AsyncSession = Depends(get_db), _=FacultyOrAdmin):
    try:
        return await program_service.get_program(db, program_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{program_id}", response_model=ProgramRead)
async def update_program(
    program_id: int, data: ProgramUpdate, db: AsyncSession = Depends(get_db), _=AdminOnly
):
    try:
        return await program_service.update_program(db, program_id, data)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_program(program_id: int, db: AsyncSession = Depends(get_db), _=AdminOnly):
    try:
        await program_service.delete_program(db, program_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
