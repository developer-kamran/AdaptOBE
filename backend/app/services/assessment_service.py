from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.user import User
from app.schemas.assessment import AssessmentCreate, AssessmentUpdate
from app.services import course_service
from app.services.exceptions import NotFoundError, ValidationError

MAX_TOTAL_WEIGHTAGE = 100.0


async def _total_weightage(
    db: AsyncSession, course_id: int, exclude_assessment_id: int | None = None
) -> float:
    stmt = select(Assessment).where(Assessment.course_id == course_id)
    if exclude_assessment_id is not None:
        stmt = stmt.where(Assessment.id != exclude_assessment_id)

    result = await db.execute(stmt)
    return sum(assessment.weightage_percent for assessment in result.scalars().all())


async def list_assessments(db: AsyncSession, course_id: int) -> list[Assessment]:
    result = await db.execute(
        select(Assessment).where(Assessment.course_id == course_id).order_by(Assessment.id)
    )
    return list(result.scalars().all())


async def get_assessment(db: AsyncSession, assessment_id: int) -> Assessment:
    assessment = await db.get(Assessment, assessment_id)
    if assessment is None:
        raise NotFoundError(f"Assessment {assessment_id} not found")
    return assessment


async def get_assessment_for_user(
    db: AsyncSession, assessment_id: int, user: User
) -> Assessment:
    assessment = await get_assessment(db, assessment_id)
    await course_service.get_course_for_user(db, assessment.course_id, user)
    return assessment


async def create_assessment(db: AsyncSession, data: AssessmentCreate, user: User) -> Assessment:
    await course_service.get_course_for_user(db, data.course_id, user)

    existing = await _total_weightage(db, data.course_id)
    if existing + data.weightage_percent > MAX_TOTAL_WEIGHTAGE:
        raise ValidationError(
            f"Total assessment weightage for this course would reach "
            f"{existing + data.weightage_percent:g}%, which exceeds {MAX_TOTAL_WEIGHTAGE:g}%"
        )

    assessment = Assessment(
        course_id=data.course_id,
        title=data.title,
        type=data.type,
        total_marks=data.total_marks,
        weightage_percent=data.weightage_percent,
        date=data.date,
        duration_minutes=data.duration_minutes,
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment


async def update_assessment(
    db: AsyncSession, assessment_id: int, data: AssessmentUpdate, user: User
) -> Assessment:
    assessment = await get_assessment_for_user(db, assessment_id, user)
    changes = data.model_dump(exclude_unset=True)

    if "weightage_percent" in changes:
        others = await _total_weightage(db, assessment.course_id, exclude_assessment_id=assessment.id)
        if others + changes["weightage_percent"] > MAX_TOTAL_WEIGHTAGE:
            raise ValidationError(
                f"Total assessment weightage for this course would reach "
                f"{others + changes['weightage_percent']:g}%, which exceeds "
                f"{MAX_TOTAL_WEIGHTAGE:g}%"
            )

    for field, value in changes.items():
        setattr(assessment, field, value)

    await db.commit()
    await db.refresh(assessment)
    return assessment


async def delete_assessment(db: AsyncSession, assessment_id: int, user: User) -> int:
    assessment = await get_assessment_for_user(db, assessment_id, user)
    course_id = assessment.course_id
    await db.delete(assessment)
    await db.commit()
    return course_id
