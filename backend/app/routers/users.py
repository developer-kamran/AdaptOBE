from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.user import UserPasswordRead, UserRead, UserUpdate
from app.services import user_service
from app.services.exceptions import ConflictError, NotFoundError, PermissionDeniedError

router = APIRouter(
    prefix="/api/v1/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_roles(UserRole.super_admin, UserRole.sub_admin))],
)


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await user_service.list_users_for_admin(db, current_user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await user_service.get_user_scoped(db, user_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc


@router.get("/{user_id}/password", response_model=UserPasswordRead)
async def get_user_password(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        password = await user_service.get_user_password(db, user_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc
    return UserPasswordRead(password=password)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await user_service.update_user(db, user_id, data, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{user_id}", response_model=UserRead)
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await user_service.deactivate_user(db, user_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc
