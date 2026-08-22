from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.assessment import AssessmentCreate, AssessmentRead, AssessmentUpdate
from app.schemas.question import (
    QuestionBulkCreateRequest,
    QuestionBulkCreateResponse,
    QuestionCreate,
    QuestionRead,
    QuestionUpdate,
    TagSuggestRequest,
    TagSuggestResponse,
)
from app.schemas.assessment_paper_import import AssessmentPaperPreview
from app.schemas.score import BulkScoreRequest, BulkScoreResponse, ScoreRead
from app.schemas.score_import import ConfirmScoreImportRequest, ScoreImportPreview
from app.services import (
    assessment_export_service,
    assessment_paper_import_service,
    assessment_service,
    attainment_service,
    clo_service,
    course_service,
    file_parsers,
    question_service,
    score_import_service,
    score_service,
)
from app.services.exceptions import (
    ConflictError,
    LLMGenerationError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])

# Assessments/scoring is a faculty-operational concern -- neither admin tier
# touches it, per the admin-hierarchy redesign.
FacultyOnly = Depends(require_roles(UserRole.faculty))

#: Score sheets are small. Mirrors enrollments.py's import upload cap.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

#: Assessment papers are real documents (can include headers/images inside
#: an otherwise-text PDF/Word file), so this gets a larger cap than the
#: tabular score-sheet upload above.
MAX_PAPER_UPLOAD_BYTES = 10 * 1024 * 1024


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
    )


@router.get("", response_model=list[AssessmentRead])
async def list_assessments(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
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
    current_user: User = FacultyOnly,
):
    try:
        return await assessment_service.create_assessment(db, data, current_user)
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc


@router.get("/{assessment_id}", response_model=AssessmentRead)
async def get_assessment(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
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
    current_user: User = FacultyOnly,
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
    current_user: User = FacultyOnly,
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
    current_user: User = FacultyOnly,
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
    current_user: User = FacultyOnly,
):
    try:
        question = await question_service.create_question(
            db, assessment_id, data, current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError, ConflictError) as exc:
        raise _translate(exc) from exc

    assessment = await assessment_service.get_assessment(db, assessment_id)
    await attainment_service.recalculate_course_attainment(db, assessment.course_id)
    return question


@router.post(
    "/{assessment_id}/questions/bulk",
    response_model=QuestionBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_questions_bulk(
    assessment_id: int,
    data: QuestionBulkCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    """Create several questions at once (e.g. N MCQ/Fill-in-the-Blank/True-
    False items), all-or-nothing."""
    try:
        questions = await question_service.bulk_create_questions(
            db, assessment_id, data.items, current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError, ConflictError) as exc:
        raise _translate(exc) from exc

    assessment = await assessment_service.get_assessment(db, assessment_id)
    await attainment_service.recalculate_course_attainment(db, assessment.course_id)
    return QuestionBulkCreateResponse(created=questions)


@router.patch("/questions/{question_id}", response_model=QuestionRead)
async def update_question(
    question_id: int,
    data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        question, course_id = await question_service.update_question(
            db, question_id, data, current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError, ConflictError) as exc:
        raise _translate(exc) from exc

    # Changing marks or the CLO tag changes attainment (section 8).
    await attainment_service.recalculate_course_attainment(db, course_id)
    return question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
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
    current_user: User = FacultyOnly,
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
    current_user: User = FacultyOnly,
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
    current_user: User = FacultyOnly,
):
    try:
        saved, recalculated = await score_service.bulk_enter_scores(
            db, assessment_id, data, current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc

    return BulkScoreResponse(saved=saved, recalculated_students=recalculated)


async def _exam_export_context(db: AsyncSession, assessment_id: int, current_user: User):
    assessment = await assessment_service.get_assessment_for_user(db, assessment_id, current_user)
    course = await course_service.get_course(db, assessment.course_id)
    instructor = await db.get(User, course.owner_faculty_id)
    questions = await question_service.list_questions(db, assessment_id)
    return course, assessment, instructor.full_name if instructor else "—", questions


@router.get("/{assessment_id}/export/pdf")
async def export_assessment_pdf(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        course, assessment, instructor_name, questions = await _exam_export_context(
            db, assessment_id, current_user
        )
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    pdf_bytes = assessment_export_service.build_exam_pdf(course, assessment, instructor_name, questions)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        # `inline`, not `attachment` -- the frontend renders this in a preview
        # iframe; the reader can still save it from there.
        headers={"Content-Disposition": f'inline; filename="{assessment.title}.pdf"'},
    )


@router.get("/{assessment_id}/export/docx")
async def export_assessment_docx(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        course, assessment, instructor_name, questions = await _exam_export_context(
            db, assessment_id, current_user
        )
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    docx_bytes = assessment_export_service.build_exam_docx(course, assessment, instructor_name, questions)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{assessment.title}.docx"'},
    )


@router.post("/{assessment_id}/scores/import/preview", response_model=ScoreImportPreview)
async def preview_score_import(
    assessment_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    """Parse an uploaded score sheet and classify each row. Saves nothing."""
    try:
        assessment = await assessment_service.get_assessment_for_user(db, assessment_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    filename = file.filename or ""
    if not filename.lower().endswith(file_parsers.SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported file type. Upload one of: {', '.join(file_parsers.SUPPORTED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large (limit {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The file is empty")

    try:
        return await score_import_service.build_preview(db, assessment, content, filename)
    except file_parsers.FileParseError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post(
    "/{assessment_id}/scores/import/confirm",
    response_model=BulkScoreResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_score_import(
    assessment_id: int,
    data: ConfirmScoreImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    """Delegates to the same `bulk_enter_scores` the manual Score Entry grid
    uses -- no parallel write path, same validation applies at commit time."""
    try:
        saved, recalculated = await score_service.bulk_enter_scores(
            db, assessment_id, BulkScoreRequest(scores=data.scores), current_user
        )
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc

    return BulkScoreResponse(saved=saved, recalculated_students=recalculated)


@router.post("/{assessment_id}/paper-import/preview", response_model=AssessmentPaperPreview)
async def preview_paper_import(
    assessment_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    """Extract questions (and header metadata for verification) from an
    uploaded assessment paper (the "Upload Assessment Paper" feature).
    Writes nothing -- the faculty reviews the extracted questions and
    imports the ones they approve via the existing bulk question-create
    endpoint, exactly like the manual bulk-add flow."""
    try:
        assessment = await assessment_service.get_assessment_for_user(db, assessment_id, current_user)
        course = await course_service.get_course(db, assessment.course_id)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc

    filename = file.filename or ""
    if not filename.lower().endswith(file_parsers.DOCUMENT_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported file type. Upload one of: {', '.join(file_parsers.DOCUMENT_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_PAPER_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large (limit {MAX_PAPER_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The file is empty")

    instructor = await db.get(User, course.owner_faculty_id)
    clos = await clo_service.list_clos(db, course.id)

    try:
        return await assessment_paper_import_service.build_preview(
            course, assessment, instructor, clos, content, filename
        )
    except file_parsers.FileParseError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except LLMGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
