from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import embeddings
from app.models.assessment import Assessment, AssessmentType
from app.models.clo import CLO
from app.models.question import Question, QuestionType
from app.models.user import User
from app.schemas.question import CLOTagSuggestion, QuestionCreate, QuestionUpdate
from app.services import assessment_service
from app.services.exceptions import ConflictError, NotFoundError, ValidationError

# Lab and Project are assessment-level types (Assessment.type), not
# selectable question types within a normal quiz/assignment/midterm/final --
# see CHANGELOG.md. A "lab"/"project" assessment is managed as a small set
# of components instead, but each component is still stored as a `Question`
# row with a matching `question_type` so Score Entry works unchanged. This
# keeps the two in lockstep either way.
_ASSESSMENT_TYPE_TO_QUESTION_TYPE = {
    AssessmentType.lab: QuestionType.lab,
    AssessmentType.project: QuestionType.project,
}


def _validate_question_type_for_assessment(
    assessment: Assessment, question_type: QuestionType
) -> None:
    required = _ASSESSMENT_TYPE_TO_QUESTION_TYPE.get(assessment.type)
    if required is not None:
        if question_type != required:
            raise ValidationError(
                f"A {assessment.type.value} assessment can only contain "
                f"{required.value} components"
            )
    elif question_type in _ASSESSMENT_TYPE_TO_QUESTION_TYPE.values():
        raise ValidationError(
            f"'{question_type.value}' is only valid for a {question_type.value} assessment"
        )


async def list_questions(db: AsyncSession, assessment_id: int) -> list[Question]:
    result = await db.execute(
        select(Question)
        .where(Question.assessment_id == assessment_id)
        .order_by(Question.question_number)
    )
    return list(result.scalars().all())


async def get_question(db: AsyncSession, question_id: int) -> Question:
    question = await db.get(Question, question_id)
    if question is None:
        raise NotFoundError(f"Question {question_id} not found")
    return question


async def _validate_clo_belongs_to_course(
    db: AsyncSession, clo_id: int | None, course_id: int
) -> None:
    """A question may only be tagged with a CLO from its own course."""
    if clo_id is None:
        return

    clo = await db.get(CLO, clo_id)
    if clo is None:
        raise NotFoundError(f"CLO {clo_id} not found")
    if clo.course_id != course_id:
        raise ValidationError("A question can only be tagged with a CLO from its own course")


async def _ensure_unique_number(
    db: AsyncSession,
    assessment_id: int,
    question_number: int,
    exclude_question_id: int | None = None,
    reserved_numbers: frozenset[int] = frozenset(),
) -> None:
    """A question number must be unique within its own assessment (a
    different assessment may reuse the same number). `reserved_numbers`
    additionally covers numbers claimed earlier in the same batch, for
    `bulk_create_questions`, which is validated before anything is inserted."""
    if question_number in reserved_numbers:
        raise ConflictError(
            f"Question number {question_number} is used more than once in this request"
        )

    stmt = select(Question.id).where(
        Question.assessment_id == assessment_id, Question.question_number == question_number
    )
    if exclude_question_id is not None:
        stmt = stmt.where(Question.id != exclude_question_id)

    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            f"Question number {question_number} already exists in this assessment"
        )


async def _existing_marks_total(
    db: AsyncSession, assessment_id: int, exclude_question_id: int | None = None
) -> float:
    stmt = select(Question).where(Question.assessment_id == assessment_id)
    if exclude_question_id is not None:
        stmt = stmt.where(Question.id != exclude_question_id)
    result = await db.execute(stmt)
    return sum(q.marks for q in result.scalars().all())


async def _ensure_within_marks_budget(
    db: AsyncSession,
    assessment_id: int,
    total_marks: float,
    new_marks_total: float,
    exclude_question_id: int | None = None,
) -> None:
    existing = await _existing_marks_total(db, assessment_id, exclude_question_id)
    if existing + new_marks_total > total_marks:
        raise ValidationError(
            f"Total question marks for this assessment would reach "
            f"{existing + new_marks_total:g}, which exceeds the assessment's "
            f"total of {total_marks:g}"
        )


async def create_question(
    db: AsyncSession, assessment_id: int, data: QuestionCreate, user: User
) -> Question:
    assessment = await assessment_service.get_assessment_for_user(db, assessment_id, user)
    _validate_question_type_for_assessment(assessment, data.question_type)
    await _validate_clo_belongs_to_course(db, data.clo_id, assessment.course_id)
    await _ensure_unique_number(db, assessment_id, data.question_number)
    await _ensure_within_marks_budget(db, assessment_id, assessment.total_marks, data.marks)

    question = Question(
        assessment_id=assessment_id,
        question_number=data.question_number,
        marks=data.marks,
        clo_id=data.clo_id,
        text=data.text,
        question_type=data.question_type,
        type_data=data.type_data,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question


async def bulk_create_questions(
    db: AsyncSession, assessment_id: int, items: list[QuestionCreate], user: User
) -> list[Question]:
    """Create several questions (e.g. a batch of MCQ/Fill-in-the-Blank/True-
    False items) in one all-or-nothing transaction, so a partially-valid
    batch never leaves the assessment with some items created and some not."""
    assessment = await assessment_service.get_assessment_for_user(db, assessment_id, user)

    reserved: set[int] = set()
    for item in items:
        _validate_question_type_for_assessment(assessment, item.question_type)
        await _validate_clo_belongs_to_course(db, item.clo_id, assessment.course_id)
        await _ensure_unique_number(
            db, assessment_id, item.question_number, reserved_numbers=reserved
        )
        reserved.add(item.question_number)

    batch_marks_total = sum(item.marks for item in items)
    await _ensure_within_marks_budget(
        db, assessment_id, assessment.total_marks, batch_marks_total
    )

    questions = [
        Question(
            assessment_id=assessment_id,
            question_number=item.question_number,
            marks=item.marks,
            clo_id=item.clo_id,
            text=item.text,
            question_type=item.question_type,
            type_data=item.type_data,
        )
        for item in items
    ]
    db.add_all(questions)
    await db.commit()
    for question in questions:
        await db.refresh(question)
    return questions


async def update_question(
    db: AsyncSession, question_id: int, data: QuestionUpdate, user: User
) -> tuple[Question, int]:
    """Returns the question plus its course id, so callers can trigger recalculation."""
    question = await get_question(db, question_id)
    assessment = await assessment_service.get_assessment_for_user(
        db, question.assessment_id, user
    )

    changes = data.model_dump(exclude_unset=True)
    if "question_type" in changes:
        _validate_question_type_for_assessment(assessment, changes["question_type"])
    if "clo_id" in changes:
        await _validate_clo_belongs_to_course(db, changes["clo_id"], assessment.course_id)
    if "question_number" in changes:
        await _ensure_unique_number(
            db, question.assessment_id, changes["question_number"], exclude_question_id=question.id
        )
    if "marks" in changes:
        await _ensure_within_marks_budget(
            db,
            question.assessment_id,
            assessment.total_marks,
            changes["marks"],
            exclude_question_id=question.id,
        )

    for field, value in changes.items():
        setattr(question, field, value)

    await db.commit()
    await db.refresh(question)
    return question, assessment.course_id


async def delete_question(db: AsyncSession, question_id: int, user: User) -> int:
    question = await get_question(db, question_id)
    assessment = await assessment_service.get_assessment_for_user(
        db, question.assessment_id, user
    )
    await db.delete(question)
    await db.commit()
    return assessment.course_id


async def suggest_clo_tags(
    db: AsyncSession, course_id: int, text: str, limit: int = 3
) -> list[CLOTagSuggestion]:
    """Rank a course's CLOs by how closely their wording matches a question.

    Mirrors the CLO-to-PLO suggestion approach: encode the query text, then let
    pgvector do the cosine comparison against stored CLO embeddings.
    """
    query_embedding = await embeddings.aencode_text(text)

    distance = CLO.embedding.cosine_distance(query_embedding).label("distance")
    stmt = (
        select(CLO, distance)
        .where(CLO.course_id == course_id, CLO.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    rows = await db.execute(stmt)

    return [
        CLOTagSuggestion(
            clo_id=clo.id,
            code=clo.code,
            title=clo.title,
            similarity_score=round(1.0 - float(dist), 6),
        )
        for clo, dist in rows.all()
    ]
