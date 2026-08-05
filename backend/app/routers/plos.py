from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import UserRole
from app.schemas.plo import PLOCreate, PLORead, PLOUpdate
from app.services import plo_service
from app.services.exceptions import ConflictError, NotFoundError

router = APIRouter(prefix="/api/v1/admin/plos", tags=["admin-plos"])

# PLOs are institutional setup, so only admins create/edit/delete them. But
# faculty need to *read* PLOs to confirm CLO-PLO mappings on their own courses
# -- without this, the mapping UI could never show a faculty user what a PLO
# actually says.
FacultyOrAdmin = Depends(require_roles(UserRole.faculty, UserRole.admin))
AdminOnly = Depends(require_roles(UserRole.admin))


@router.get("", response_model=list[PLORead])
async def list_plos(
    program_id: int | None = None, db: AsyncSession = Depends(get_db), _=FacultyOrAdmin
):
    return await plo_service.list_plos(db, program_id)


@router.post("", response_model=PLORead, status_code=status.HTTP_201_CREATED)
async def create_plo(data: PLOCreate, db: AsyncSession = Depends(get_db), _=AdminOnly):
    try:
        return await plo_service.create_plo(db, data)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{plo_id}", response_model=PLORead)
async def get_plo(plo_id: int, db: AsyncSession = Depends(get_db), _=FacultyOrAdmin):
    try:
        return await plo_service.get_plo(db, plo_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{plo_id}", response_model=PLORead)
async def update_plo(plo_id: int, data: PLOUpdate, db: AsyncSession = Depends(get_db), _=AdminOnly):
    try:
        return await plo_service.update_plo(db, plo_id, data)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{plo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plo(plo_id: int, db: AsyncSession = Depends(get_db), _=AdminOnly):
    try:
        await plo_service.delete_plo(db, plo_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
