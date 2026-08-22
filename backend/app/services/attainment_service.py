"""Direct attainment engine: turns raw scores into persisted attainment records.

The arithmetic itself lives in `attainment_math` as pure functions; this module
only gathers the inputs, applies them, and persists the results.
"""

import logging
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.attainment import AttainmentRecord
from app.models.clo import CLO
from app.models.mapping import CloPloMapping
from app.models.plo import PLO
from app.models.question import Question
from app.models.student_score import StudentScore
from app.schemas.attainment import (
    CLOAttainmentSummary,
    CourseAttainmentReport,
    HeatmapCell,
    PLOAttainmentSummary,
    StudentCLOAttainment,
    StudentProgressReport,
)
from app.services import attainment_math, course_service, enrollment_service, notifications

logger = logging.getLogger(__name__)


async def _course_questions(db: AsyncSession, course_id: int) -> list[Question]:
    result = await db.execute(
        select(Question)
        .join(Assessment, Assessment.id == Question.assessment_id)
        .where(Assessment.course_id == course_id)
    )
    return list(result.scalars().all())


async def _scores_for_questions(
    db: AsyncSession, question_ids: list[int]
) -> dict[tuple[int, int], float]:
    """Map (student_id, question_id) -> marks_obtained."""
    if not question_ids:
        return {}

    result = await db.execute(
        select(StudentScore).where(StudentScore.question_id.in_(question_ids))
    )
    return {
        (score.student_id, score.question_id): score.marks_obtained
        for score in result.scalars().all()
    }


async def recalculate_course_attainment(db: AsyncSession, course_id: int) -> int:
    """Recompute and persist every enrolled student's CLO attainment for a course.

    Attainment records are derived data, so the course's rows are replaced
    wholesale rather than patched -- that keeps the table consistent when
    questions, CLO tags or scores are edited or removed.

    Returns the number of students recalculated.
    """
    course = await course_service.get_course(db, course_id)

    clos = list(
        (await db.execute(select(CLO).where(CLO.course_id == course_id).order_by(CLO.id)))
        .scalars()
        .all()
    )
    student_ids = await enrollment_service.list_enrolled_student_ids(db, course_id)

    await db.execute(
        delete(AttainmentRecord).where(AttainmentRecord.course_id == course_id)
    )

    if not clos or not student_ids:
        await db.commit()
        await notifications.broadcast(
            {"type": "attainment.recalculated", "course_id": course_id, "student_count": 0}
        )
        return 0

    questions = await _course_questions(db, course_id)
    questions_by_clo: dict[int, list[Question]] = defaultdict(list)
    for question in questions:
        if question.clo_id is not None:
            questions_by_clo[question.clo_id].append(question)

    scores = await _scores_for_questions(db, [question.id for question in questions])

    # student_id -> clo_id -> attainment percentage
    per_student: dict[int, dict[int, float]] = defaultdict(dict)

    for clo in clos:
        clo_questions = questions_by_clo.get(clo.id, [])
        possible = sum(question.marks for question in clo_questions)

        for student_id in student_ids:
            # A missing score row means the student was absent: it counts as 0.0
            # and the student still counts toward the cohort (section 8).
            obtained = sum(
                scores.get((student_id, question.id), 0.0) for question in clo_questions
            )
            per_student[student_id][clo.id] = attainment_math.clo_attainment(obtained, possible)

    for clo in clos:
        cohort = [per_student[student_id][clo.id] for student_id in student_ids]
        average = attainment_math.class_average(cohort)
        achieved = attainment_math.is_achieved(average, course.attainment_threshold)

        for student_id in student_ids:
            db.add(
                AttainmentRecord(
                    student_id=student_id,
                    course_id=course_id,
                    clo_id=clo.id,
                    attainment_percentage=per_student[student_id][clo.id],
                    is_achieved=achieved,
                )
            )

    await db.commit()

    await notifications.broadcast(
        {
            "type": "attainment.recalculated",
            "course_id": course_id,
            "student_count": len(student_ids),
        }
    )
    return len(student_ids)


async def _course_mappings(db: AsyncSession, clo_ids: list[int]) -> list[CloPloMapping]:
    if not clo_ids:
        return []

    result = await db.execute(
        select(CloPloMapping)
        .where(CloPloMapping.clo_id.in_(clo_ids))
        .order_by(CloPloMapping.clo_id, CloPloMapping.plo_id)
    )
    return list(result.scalars().all())


async def build_course_report(db: AsyncSession, course_id: int) -> CourseAttainmentReport:
    """CLO and PLO class attainment plus the CLO-to-PLO strength heatmap."""
    course = await course_service.get_course(db, course_id)

    clos = list(
        (await db.execute(select(CLO).where(CLO.course_id == course_id).order_by(CLO.id)))
        .scalars()
        .all()
    )
    records = list(
        (
            await db.execute(
                select(AttainmentRecord).where(AttainmentRecord.course_id == course_id)
            )
        )
        .scalars()
        .all()
    )

    by_clo: dict[int, list[AttainmentRecord]] = defaultdict(list)
    for record in records:
        by_clo[record.clo_id].append(record)

    # A CLO with no tagged questions still gets a zero-filled attainment_record
    # per student (section 8's zero-division guard), which reads identically to
    # "students are failing this CLO". Only let CLOs that have actually been
    # assessed pull a PLO's attainment toward that number -- otherwise a PLO
    # whose CLOs simply haven't been assessed yet (e.g. before the Final Exam)
    # looks falsely under-attained instead of just "not yet measured".
    questions = await _course_questions(db, course_id)
    assessed_clo_ids = {question.clo_id for question in questions if question.clo_id is not None}

    clo_summaries: list[CLOAttainmentSummary] = []
    clo_averages: dict[int, float] = {}

    for clo in clos:
        clo_records = by_clo.get(clo.id, [])
        average = attainment_math.class_average(
            [record.attainment_percentage for record in clo_records]
        )
        clo_averages[clo.id] = average
        clo_summaries.append(
            CLOAttainmentSummary(
                clo_id=clo.id,
                code=clo.code,
                title=clo.title,
                bloom_level=clo.bloom_level,
                class_average=average,
                is_achieved=any(record.is_achieved for record in clo_records),
                student_count=len(clo_records),
            )
        )

    mappings = await _course_mappings(db, [clo.id for clo in clos])

    contributions: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for mapping in mappings:
        if mapping.clo_id not in assessed_clo_ids:
            continue
        contributions[mapping.plo_id].append(
            (clo_averages.get(mapping.clo_id, 0.0), mapping.strength)
        )

    plo_summaries: list[PLOAttainmentSummary] = []
    if contributions:
        plos = list(
            (await db.execute(select(PLO).where(PLO.id.in_(contributions.keys())).order_by(PLO.id)))
            .scalars()
            .all()
        )
        for plo in plos:
            plo_summaries.append(
                PLOAttainmentSummary(
                    plo_id=plo.id,
                    code=plo.code,
                    title=plo.title,
                    class_average=attainment_math.plo_attainment(contributions[plo.id]),
                )
            )

    student_count = len({record.student_id for record in records})

    return CourseAttainmentReport(
        course_id=course_id,
        threshold=course.attainment_threshold,
        student_count=student_count,
        clo_attainment=clo_summaries,
        plo_attainment=plo_summaries,
        heatmap=[
            HeatmapCell(clo_id=m.clo_id, plo_id=m.plo_id, strength=m.strength) for m in mappings
        ],
    )


async def build_student_report(
    db: AsyncSession, course_id: int, student_id: int
) -> StudentProgressReport:
    result = await db.execute(
        select(AttainmentRecord)
        .where(
            AttainmentRecord.course_id == course_id,
            AttainmentRecord.student_id == student_id,
        )
        .order_by(AttainmentRecord.clo_id)
    )

    return StudentProgressReport(
        student_id=student_id,
        course_id=course_id,
        clo_attainment=[
            StudentCLOAttainment.model_validate(record) for record in result.scalars().all()
        ],
    )
