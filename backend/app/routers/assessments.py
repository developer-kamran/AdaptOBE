from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.assessment import AssessmentCreate, AssessmentRead, AssessmentUpdate
from app.schemas.question import (
    QuestionCreate,
    QuestionRead,
    QuestionUpdate,
    TagSuggestRequest,
    TagSuggestResponse,
)
from app.schemas.score import BulkScoreRequest, BulkScoreResponse, ScoreRead
from app.services import (
    assessment_service,
    attainment_service,
    course_service,
    question_service,
    score_service,
)
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])

FacultyOrAdmin = Depends(require_roles(UserRole.faculty, UserRole.admin))


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
    )


@router.get("", response_model=list[AssessmentRead])
async def list_assessments(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        await course_service.get_course_for_user(db, course_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    return await assessment_service.list_assessments(db, course_id)


@router.post("", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    data: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        return await assessment_service.create_assessment(db, data, current_user)
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc


@router.get("/{assessment_id}", response_model=AssessmentRead)
async def get_assessment(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        return await assessment_service.get_assessment_for_user(db, assessment_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc


@router.patch("/{assessment_id}", response_model=AssessmentRead)
async def update_assessment(
    assessment_id: int,
    data: AssessmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        return await assessment_service.update_assessment(
            db, assessment_id, data, current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        course_id = await assessment_service.delete_assessment(
            db, assessment_id, current_user
        )
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    # Removing an assessment removes its questions, so attainment must be redone.
    await attainment_service.recalculate_course_attainment(db, course_id)


@router.get("/{assessment_id}/questions", response_model=list[QuestionRead])
async def list_questions(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        await assessment_service.get_assessment_for_user(db, assessment_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    return await question_service.list_questions(db, assessment_id)


@router.post(
    "/{assessment_id}/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED
)
async def create_question(
    assessment_id: int,
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        question = await question_service.create_question(
            db, assessment_id, data, current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc

    assessment = await assessment_service.get_assessment(db, assessment_id)
    await attainment_service.recalculate_course_attainment(db, assessment.course_id)
    return question


@router.patch("/questions/{question_id}", response_model=QuestionRead)
async def update_question(
    question_id: int,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        question, course_id = await question_service.update_question(
            db, question_id, data, current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc

    # Changing marks or the CLO tag changes attainment (section 8).
    await attainment_service.recalculate_course_attainment(db, course_id)
    return question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        course_id = await question_service.delete_question(db, question_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    await attainment_service.recalculate_course_attainment(db, course_id)


@router.post("/{assessment_id}/questions/suggest-tag", response_model=TagSuggestResponse)
async def suggest_question_tag(
    assessment_id: int,
    data: TagSuggestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        assessment = await assessment_service.get_assessment_for_user(
            db, assessment_id, current_user
        )
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    suggestions = await question_service.suggest_clo_tags(
        db, assessment.course_id, data.text, data.limit
    )
    return TagSuggestResponse(suggestions=suggestions)


@router.get("/{assessment_id}/scores", response_model=list[ScoreRead])
async def list_scores(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        await assessment_service.get_assessment_for_user(db, assessment_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    return await score_service.list_scores(db, assessment_id)


@router.post(
    "/{assessment_id}/scores",
    response_model=BulkScoreResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_enter_scores(
    assessment_id: int,
    data: BulkScoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    try:
        saved, recalculated = await score_service.bulk_enter_scores(
            db, assessment_id, data, current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc

    return BulkScoreResponse(saved=saved, recalculated_students=recalculated)
