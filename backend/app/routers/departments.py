from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import UserRole
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.services import department_service
from app.services.exceptions import ConflictError, NotFoundError

router = APIRouter(
    prefix="/api/v1/admin/departments",
    tags=["admin-departments"],
    dependencies=[Depends(require_roles(UserRole.super_admin))],
)


@router.get("", response_model=list[DepartmentRead])
async def list_departments(db: AsyncSession = Depends(get_db)):
    return await department_service.list_departments(db)


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
async def create_department(data: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await department_service.create_department(db, data)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{department_id}", response_model=DepartmentRead)
async def get_department(department_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await department_service.get_department(db, department_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{department_id}", response_model=DepartmentRead)
async def update_department(
    department_id: int, data: DepartmentUpdate, db: AsyncSession = Depends(get_db)
):
    try:
        return await department_service.update_department(db, department_id, data)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(department_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await department_service.delete_department(db, department_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
