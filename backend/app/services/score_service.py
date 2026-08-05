from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import CourseEnrollment
from app.models.question import Question
from app.models.student_score import StudentScore
from app.models.user import User
from app.schemas.score import BulkScoreRequest
from app.services import assessment_service, attainment_service
from app.services.exceptions import NotFoundError, ValidationError


async def bulk_enter_scores(
    db: AsyncSession, assessment_id: int, data: BulkScoreRequest, user: User
) -> tuple[int, int]:
    """Validate and persist a batch of scores, then recalculate attainment.

    Returns (scores saved, students recalculated). The whole batch is validated
    before anything is written, so a single bad row cannot leave a half-entered
    assessment behind.
    """
    assessment = await assessment_service.get_assessment_for_user(db, assessment_id, user)

    questions = {
        question.id: question
        for question in (
            await db.execute(
                select(Question).where(Question.assessment_id == assessment_id)
            )
        )
        .scalars()
        .all()
    }

    enrolled = set(
        (
            await db.execute(
                select(CourseEnrollment.student_id).where(
                    CourseEnrollment.course_id == assessment.course_id
                )
            )
        )
        .scalars()
        .all()
    )

    for entry in data.scores:
        question = questions.get(entry.question_id)
        if question is None:
            raise NotFoundError(
                f"Question {entry.question_id} does not belong to assessment {assessment_id}"
            )
        if entry.marks_obtained > question.marks:
            raise ValidationError(
                f"Question {entry.question_id}: marks_obtained "
                f"({entry.marks_obtained:g}) exceeds the question's marks "
                f"({question.marks:g})"
            )
        if entry.student_id not in enrolled:
            raise ValidationError(
                f"Student {entry.student_id} is not enrolled in this course"
            )

    existing = {
        (score.student_id, score.question_id): score
        for score in (
            await db.execute(
                select(StudentScore).where(
                    StudentScore.question_id.in_(list(questions.keys()) or [0])
                )
            )
        )
        .scalars()
        .all()
    }

    for entry in data.scores:
        key = (entry.student_id, entry.question_id)
        if key in existing:
            existing[key].marks_obtained = entry.marks_obtained
        else:
            db.add(
                StudentScore(
                    question_id=entry.question_id,
                    student_id=entry.student_id,
                    marks_obtained=entry.marks_obtained,
                )
            )

    await db.commit()

    recalculated = await attainment_service.recalculate_course_attainment(
        db, assessment.course_id
    )
    return len(data.scores), recalculated


async def list_scores(db: AsyncSession, assessment_id: int) -> list[StudentScore]:
    result = await db.execute(
        select(StudentScore)
        .join(Question, Question.id == StudentScore.question_id)
        .where(Question.assessment_id == assessment_id)
        .order_by(StudentScore.student_id, StudentScore.question_id)
    )
    return list(result.scalars().all())
