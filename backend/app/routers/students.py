from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import UserRole
from app.schemas.user import UserRead
from app.services import user_service

router = APIRouter(prefix="/api/v1/students", tags=["students"])


@router.get("", response_model=list[UserRead])
async def list_students(
    db: AsyncSession = Depends(get_db),
    _: UserRead = Depends(require_roles(UserRole.faculty, UserRole.admin)),
):
    """Active students only, for faculty enrolling a course. Narrower than the
    admin-only full user directory in /admin/users."""
    return await user_service.list_active_students(db)
