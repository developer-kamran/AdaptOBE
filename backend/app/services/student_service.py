"""Student-portal read models and the adaptive quiz (Module 6).

Everything here is scoped to the *authenticated* student: a student may only
ever see their own attainment, scores, and quizzes. Course-specific calls first
assert enrolment, so a student cannot read another course by editing the URL.

The heavy lifting (attainment, CLO/PLO math) was already done by earlier
modules and persisted; this module only projects it into per-student views and
adds the adaptive quiz, whose pure rules live in `quiz_logic.py`.
"""

import random
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.attainment import AttainmentRecord
from app.models.clo import CLO
from app.models.course import Course
from app.models.enrollment import CourseEnrollment
from app.models.question import Question
from app.models.student_score import StudentScore
from app.models.user import User
from app.schemas.student import (
    AdaptiveQuiz,
    CourseProgress,
    CourseScoreHistory,
    QuizOption,
    QuizQuestion,
    QuizResult,
    QuizResultItem,
    QuizSubmit,
    ScoreHistoryItem,
    StudentCLOProgress,
    StudentProgressResponse,
)
from app.services import quiz_logic
from app.services.attainment_math import clo_attainment
from app.services.exceptions import PermissionDeniedError


async def _enrolled_course_ids(db: AsyncSession, student_id: int) -> list[int]:
    result = await db.execute(
        select(CourseEnrollment.course_id)
        .where(CourseEnrollment.student_id == student_id)
        .order_by(CourseEnrollment.course_id)
    )
    return list(result.scalars().all())


async def _ensure_enrolled(db: AsyncSession, student_id: int, course_id: int) -> None:
    result = await db.execute(
        select(CourseEnrollment.id).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise PermissionDeniedError("You are not enrolled in this course")


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


async def get_progress(db: AsyncSession, student: User) -> StudentProgressResponse:
    """Per-course CLO attainment for the student, with personal weak-CLO flags."""
    course_ids = await _enrolled_course_ids(db, student.id)
    if not course_ids:
        return StudentProgressResponse(overall_average=0.0, courses=[])

    courses = {
        course.id: course
        for course in (await db.execute(select(Course).where(Course.id.in_(course_ids))))
        .scalars()
        .all()
    }
    clos = {
        clo.id: clo
        for clo in (await db.execute(select(CLO).where(CLO.course_id.in_(course_ids))))
        .scalars()
        .all()
    }
    records = (
        await db.execute(
            select(AttainmentRecord).where(
                AttainmentRecord.student_id == student.id,
                AttainmentRecord.course_id.in_(course_ids),
            )
        )
    ).scalars().all()

    by_course: dict[int, list[AttainmentRecord]] = defaultdict(list)
    for record in records:
        by_course[record.course_id].append(record)

    course_progress: list[CourseProgress] = []
    all_percentages: list[float] = []

    for course_id in course_ids:
        course = courses[course_id]
        course_records = sorted(by_course.get(course_id, []), key=lambda r: r.clo_id)

        clo_progress: list[StudentCLOProgress] = []
        for record in course_records:
            clo = clos.get(record.clo_id)
            # A student's *personal* gap: their own attainment below threshold,
            # not the class-level is_achieved flag.
            is_weak = record.attainment_percentage < course.attainment_threshold
            all_percentages.append(record.attainment_percentage)
            clo_progress.append(
                StudentCLOProgress(
                    clo_id=record.clo_id,
                    code=clo.code if clo else f"CLO-{record.clo_id}",
                    title=clo.title if clo else "",
                    attainment_percentage=record.attainment_percentage,
                    is_weak=is_weak,
                )
            )

        course_progress.append(
            CourseProgress(
                course_id=course_id,
                code=course.code,
                name=course.name,
                semester=course.semester,
                threshold=course.attainment_threshold,
                overall_average=_mean([c.attainment_percentage for c in clo_progress]),
                weak_clo_count=sum(1 for c in clo_progress if c.is_weak),
                clo_progress=clo_progress,
            )
        )

    return StudentProgressResponse(
        overall_average=_mean(all_percentages), courses=course_progress
    )


async def get_course_scores(
    db: AsyncSession, student: User, course_id: int
) -> CourseScoreHistory:
    await _ensure_enrolled(db, student.id, course_id)

    assessments = list(
        (await db.execute(select(Assessment).where(Assessment.course_id == course_id).order_by(Assessment.id)))
        .scalars()
        .all()
    )
    questions = list(
        (
            await db.execute(
                select(Question)
                .join(Assessment, Assessment.id == Question.assessment_id)
                .where(Assessment.course_id == course_id)
            )
        )
        .scalars()
        .all()
    )
    questions_by_assessment: dict[int, list[Question]] = defaultdict(list)
    for question in questions:
        questions_by_assessment[question.assessment_id].append(question)

    question_ids = [q.id for q in questions]
    scores: dict[int, float] = {}
    if question_ids:
        for score in (
            await db.execute(
                select(StudentScore).where(
                    StudentScore.question_id.in_(question_ids),
                    StudentScore.student_id == student.id,
                )
            )
        ).scalars().all():
            scores[score.question_id] = score.marks_obtained

    items: list[ScoreHistoryItem] = []
    for assessment in assessments:
        aq = questions_by_assessment.get(assessment.id, [])
        obtained = sum(scores.get(q.id, 0.0) for q in aq)
        items.append(
            ScoreHistoryItem(
                assessment_id=assessment.id,
                title=assessment.title,
                type=assessment.type.value,
                obtained=round(obtained, 2),
                total_marks=assessment.total_marks,
                percentage=clo_attainment(obtained, assessment.total_marks),
            )
        )

    return CourseScoreHistory(course_id=course_id, items=items)


async def _auto_gradable_questions(db: AsyncSession, course_id: int) -> list[Question]:
    result = await db.execute(
        select(Question)
        .join(Assessment, Assessment.id == Question.assessment_id)
        .where(
            Assessment.course_id == course_id,
            Question.clo_id.is_not(None),
            Question.question_type.in_(quiz_logic.AUTO_GRADABLE_TYPES),
        )
    )
    return list(result.scalars().all())


async def _clo_weakness(
    db: AsyncSession, student_id: int, course_id: int
) -> dict[int, float]:
    """clo_id -> weakness (100 - the student's attainment); missing -> 100."""
    records = (
        await db.execute(
            select(AttainmentRecord).where(
                AttainmentRecord.student_id == student_id,
                AttainmentRecord.course_id == course_id,
            )
        )
    ).scalars().all()
    return {record.clo_id: 100.0 - record.attainment_percentage for record in records}


async def generate_adaptive_quiz(
    db: AsyncSession, student: User, course_id: int, size: int = quiz_logic.DEFAULT_QUIZ_SIZE
) -> AdaptiveQuiz:
    """Build a practice quiz weighted toward the student's weakest CLOs.

    Draws only from auto-gradable questions (MCQ / True-False / Fill-blank),
    allocating more questions to CLOs the student is weaker on, and strips the
    correct answers before returning anything to the student.
    """
    await _ensure_enrolled(db, student.id, course_id)

    questions = await _auto_gradable_questions(db, course_id)
    by_clo: dict[int, list[Question]] = defaultdict(list)
    for question in questions:
        by_clo[question.clo_id].append(question)

    available = {clo_id: len(qs) for clo_id, qs in by_clo.items()}
    weakness = await _clo_weakness(db, student.id, course_id)
    allocation = quiz_logic.allocate_quiz_slots(weakness, available, size)

    clos = {
        clo.id: clo
        for clo in (await db.execute(select(CLO).where(CLO.course_id == course_id))).scalars().all()
    }

    quiz_questions: list[QuizQuestion] = []
    for clo_id, count in allocation.items():
        chosen = random.sample(by_clo[clo_id], count)
        for question in chosen:
            options = None
            if question.question_type.value == "mcq" and question.type_data:
                options = [
                    QuizOption(label=opt.get("label", ""), text=opt.get("text"))
                    for opt in question.type_data.get("options", [])
                ]
            quiz_questions.append(
                QuizQuestion(
                    question_id=question.id,
                    clo_id=clo_id,
                    clo_code=clos[clo_id].code if clo_id in clos else f"CLO-{clo_id}",
                    question_type=question.question_type,
                    text=question.text or "",
                    options=options,
                )
            )

    return AdaptiveQuiz(course_id=course_id, questions=quiz_questions)


async def grade_adaptive_quiz(
    db: AsyncSession, student: User, course_id: int, submit: QuizSubmit
) -> QuizResult:
    """Grade submitted answers against each question's stored correct answer.

    This is practice: it is never written to `student_scores` and never affects
    official attainment. It only tells the student how they did and which CLOs
    to keep working on.
    """
    await _ensure_enrolled(db, student.id, course_id)

    answers = {a.question_id: a.answer for a in submit.answers}
    if not answers:
        return QuizResult(
            course_id=course_id, total=0, correct=0, score_percentage=0.0, results=[], focus_clos=[]
        )

    questions = list(
        (
            await db.execute(
                select(Question)
                .join(Assessment, Assessment.id == Question.assessment_id)
                .where(
                    Assessment.course_id == course_id,
                    Question.id.in_(list(answers.keys())),
                )
            )
        )
        .scalars()
        .all()
    )
    clos = {
        clo.id: clo
        for clo in (await db.execute(select(CLO).where(CLO.course_id == course_id))).scalars().all()
    }

    results: list[QuizResultItem] = []
    wrong_clos: set[int] = set()
    correct_count = 0
    for question in questions:
        is_correct = quiz_logic.grade_answer(
            question.question_type, question.type_data, answers.get(question.id)
        )
        if is_correct:
            correct_count += 1
        elif question.clo_id is not None:
            wrong_clos.add(question.clo_id)

        results.append(
            QuizResultItem(
                question_id=question.id,
                clo_id=question.clo_id or 0,
                clo_code=clos[question.clo_id].code if question.clo_id in clos else "—",
                correct=is_correct,
            )
        )

    total = len(results)
    focus = sorted(clos[c].code for c in wrong_clos if c in clos)

    return QuizResult(
        course_id=course_id,
        total=total,
        correct=correct_count,
        score_percentage=round(correct_count / total * 100, 2) if total else 0.0,
        results=results,
        focus_clos=focus,
    )
