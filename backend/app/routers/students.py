from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.user import UserRead
from app.services import user_service

router = APIRouter(prefix="/api/v1/students", tags=["students"])


@router.get("", response_model=list[UserRead])
async def list_students(
    course_id: int | None = None,
    backlog: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.faculty, UserRole.sub_admin)),
):
    """Active students only, for faculty enrolling a course or a sub_admin
    managing their department. Narrower than the admin-tier full user
    directory in /admin/users, and department-scoped for a sub_admin.

    `course_id` (optional) narrows results to that course's expected
    current-batch students (by programme + semester-derived enrollment
    year); add `backlog=true` to instead search the whole department for
    students from an *earlier* batch, for adding a backlog student. See
    `user_service.list_active_students` for the exact rules."""
    return await user_service.list_active_students(db, current_user, course_id, backlog)
