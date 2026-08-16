from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.student import (
    AdaptiveQuiz,
    CourseScoreHistory,
    QuizResult,
    QuizSubmit,
    StudentProgressResponse,
)
from app.services import student_service
from app.services.exceptions import NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api/v1/student", tags=["student"])

# The student portal is student-only; faculty/admins have their own views and
# get a 403 here (verified in tests).
StudentOnly = Depends(require_roles(UserRole.student))


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))


@router.get("/progress", response_model=StudentProgressResponse)
async def my_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = StudentOnly,
):
    return await student_service.get_progress(db, current_user)


@router.get("/courses/{course_id}/scores", response_model=CourseScoreHistory)
async def my_course_scores(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = StudentOnly,
):
    try:
        return await student_service.get_course_scores(db, current_user, course_id)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc


@router.get("/courses/{course_id}/adaptive-quiz", response_model=AdaptiveQuiz)
async def adaptive_quiz(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = StudentOnly,
):
    try:
        return await student_service.generate_adaptive_quiz(db, current_user, course_id)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc


@router.post("/courses/{course_id}/adaptive-quiz/submit", response_model=QuizResult)
async def submit_adaptive_quiz(
    course_id: int,
    submit: QuizSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = StudentOnly,
):
    try:
        return await student_service.grade_adaptive_quiz(db, current_user, course_id, submit)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc
