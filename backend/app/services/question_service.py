from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import embeddings
from app.models.clo import CLO
from app.models.question import Question
from app.models.user import User
from app.schemas.question import CLOTagSuggestion, QuestionCreate, QuestionUpdate
from app.services import assessment_service
from app.services.exceptions import NotFoundError, ValidationError


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


async def create_question(
    db: AsyncSession, assessment_id: int, data: QuestionCreate, user: User
) -> Question:
    assessment = await assessment_service.get_assessment_for_user(db, assessment_id, user)
    await _validate_clo_belongs_to_course(db, data.clo_id, assessment.course_id)

    question = Question(
        assessment_id=assessment_id,
        question_number=data.question_number,
        marks=data.marks,
        clo_id=data.clo_id,
        text=data.text,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question


async def update_question(
    db: AsyncSession, question_id: int, data: QuestionUpdate, user: User
) -> tuple[Question, int]:
    """Returns the question plus its course id, so callers can trigger recalculation."""
    question = await get_question(db, question_id)
    assessment = await assessment_service.get_assessment_for_user(
        db, question.assessment_id, user
    )

    changes = data.model_dump(exclude_unset=True)
    if "clo_id" in changes:
        await _validate_clo_belongs_to_course(db, changes["clo_id"], assessment.course_id)

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
