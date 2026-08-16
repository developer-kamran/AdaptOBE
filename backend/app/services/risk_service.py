"""ML risk-prediction orchestration (Module 5).

Gathers each enrolled student's five-feature vector from existing data
(attendance, quiz/assignment/midterm scores, current CLO attainment), runs the
XGBoost model in `app/ml/risk_model.py`, and persists the results. The model
math and the pure feature/label rules live elsewhere (`risk_model` / `risk_math`);
this module only wires the database to them, the same way `attainment_service`
wires the DB to `attainment_math`.

Predictions are derived data: a course's rows are deleted and re-inserted on
every run, never patched -- identical to how the attainment engine treats
`attainment_records`.
"""

import logging
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import risk_model
from app.models.assessment import Assessment, AssessmentType
from app.models.attainment import AttainmentRecord
from app.models.prediction import RiskLevel, StudentPrediction
from app.models.question import Question
from app.models.student_score import StudentScore
from app.models.user import User
from app.schemas.prediction import (
    FeatureContribution,
    LearningGapCLO,
    RiskPredictionReport,
    ShapExplanation,
    SkippedStudent,
    StoredPrediction,
    StoredPredictionReport,
    StudentRiskPrediction,
)
from app.services import (
    attainment_service,
    course_service,
    enrollment_service,
    notifications,
    risk_math,
)
from app.services.attainment_math import clo_attainment

logger = logging.getLogger(__name__)

# Assessment types that feed the three exam-derived features.
_QUIZ = AssessmentType.quiz
_ASSIGNMENT = AssessmentType.assignment
_MIDTERM = AssessmentType.midterm


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


async def _student_features(
    db: AsyncSession, course_id: int, student_ids: list[int]
) -> tuple[dict[int, dict[str, float]], dict[int, int]]:
    """Compute the five features (and an assessment-record count) per student.

    Returns (features_by_student, record_count_by_student). `record_count` is
    the number of assessments a student has any score in -- the >=5 gate from
    CLAUDE.md section 9.
    """
    assessments = list(
        (await db.execute(select(Assessment).where(Assessment.course_id == course_id)))
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

    question_ids = [question.id for question in questions]
    scores: dict[tuple[int, int], float] = {}
    if question_ids:
        for score in (
            (await db.execute(select(StudentScore).where(StudentScore.question_id.in_(question_ids))))
            .scalars()
            .all()
        ):
            scores[(score.student_id, score.question_id)] = score.marks_obtained

    # current_avg_clo_attainment from the attainment engine's persisted output.
    clo_by_student: dict[int, list[float]] = defaultdict(list)
    for record in (
        (await db.execute(select(AttainmentRecord).where(AttainmentRecord.course_id == course_id)))
        .scalars()
        .all()
    ):
        clo_by_student[record.student_id].append(record.attainment_percentage)

    from app.services.attendance_service import attendance_map

    attendance = await attendance_map(db, course_id)

    features: dict[int, dict[str, float]] = {}
    record_counts: dict[int, int] = {}

    for student_id in student_ids:
        by_type: dict[AssessmentType, list[float]] = defaultdict(list)
        records = 0

        for assessment in assessments:
            aq = questions_by_assessment.get(assessment.id, [])
            possible = sum(q.marks for q in aq)
            has_score = any((student_id, q.id) in scores for q in aq)
            if has_score:
                records += 1
            obtained = sum(scores.get((student_id, q.id), 0.0) for q in aq)
            by_type[assessment.type].append(clo_attainment(obtained, possible))

        features[student_id] = {
            "attendance_percentage": attendance.get(student_id, 0.0),
            "quiz_average_percentage": _mean(by_type.get(_QUIZ, [])),
            "assignment_average_percentage": _mean(by_type.get(_ASSIGNMENT, [])),
            "midterm_score_percentage": _mean(by_type.get(_MIDTERM, [])),
            "current_avg_clo_attainment": _mean(clo_by_student.get(student_id, [])),
        }
        record_counts[student_id] = records

    return features, record_counts


async def _learning_gaps(
    db: AsyncSession, course_id: int, threshold: float
) -> list[LearningGapCLO]:
    """CLOs whose class-average attainment sits below the course threshold.

    Reuses the attainment engine's own course report rather than recomputing
    CLO averages, so "below threshold" here means exactly what it means on the
    faculty dashboard. CLOs with no attainment data yet are not flagged.
    """
    report = await attainment_service.build_course_report(db, course_id)
    return [
        LearningGapCLO(
            clo_id=clo.clo_id,
            code=clo.code,
            title=clo.title,
            class_average=clo.class_average,
            threshold=threshold,
        )
        for clo in report.clo_attainment
        if clo.student_count > 0 and not clo.is_achieved
    ]


async def predict_course_risk(
    db: AsyncSession, course_id: int, user: User
) -> RiskPredictionReport:
    course = await course_service.get_course_for_user(db, course_id, user)
    student_ids = await enrollment_service.list_enrolled_student_ids(db, course_id)

    students = {
        student.id: student
        for student in (
            (await db.execute(select(User).where(User.id.in_(student_ids or [0])))).scalars().all()
        )
    }

    features, record_counts = await _student_features(db, course_id, student_ids)

    predictable = [sid for sid in student_ids if risk_math.has_enough_records(record_counts[sid])]
    skipped_ids = [sid for sid in student_ids if sid not in predictable]

    rows = [risk_math.assemble_feature_row(features[sid]) for sid in predictable]
    model_predictions = await risk_model.apredict(rows)

    # Derived data: replace the course's predictions wholesale.
    await db.execute(
        delete(StudentPrediction).where(StudentPrediction.course_id == course_id)
    )

    predictions: list[StudentRiskPrediction] = []
    for sid, prediction in zip(predictable, model_predictions):
        student = students.get(sid)
        shap_payload = prediction.to_shap_explanation()
        db.add(
            StudentPrediction(
                student_id=sid,
                course_id=course_id,
                risk_level=RiskLevel(prediction.risk_level),
                confidence_score=prediction.confidence,
                predicted_score=prediction.predicted_score,
                shap_explanation=shap_payload,
            )
        )
        predictions.append(
            StudentRiskPrediction(
                student_id=sid,
                full_name=student.full_name if student else "",
                seat_no=student.seat_no if student else None,
                risk_level=RiskLevel(prediction.risk_level),
                confidence_score=prediction.confidence,
                predicted_score=prediction.predicted_score,
                features=features[sid],
                shap_explanation=ShapExplanation(
                    base_value=shap_payload["base_value"],
                    predicted_risk=shap_payload["predicted_risk"],
                    confidence=shap_payload["confidence"],
                    feature_contributions=[
                        FeatureContribution(**c) for c in shap_payload["feature_contributions"]
                    ],
                ),
            )
        )

    await db.commit()

    skipped = [
        SkippedStudent(
            student_id=sid,
            full_name=students[sid].full_name if sid in students else "",
            seat_no=students[sid].seat_no if sid in students else None,
            reason="insufficient_assessment_records",
            assessment_records=record_counts[sid],
        )
        for sid in skipped_ids
    ]

    learning_gaps = await _learning_gaps(db, course_id, course.attainment_threshold)

    await notifications.broadcast(
        {
            "type": "risk.predicted",
            "course_id": course_id,
            "predicted_count": len(predictions),
        }
    )

    return RiskPredictionReport(
        course_id=course_id,
        threshold=course.attainment_threshold,
        predicted_count=len(predictions),
        predictions=predictions,
        skipped=skipped,
        learning_gaps=learning_gaps,
    )


async def get_stored_predictions(
    db: AsyncSession, course_id: int, user: User
) -> StoredPredictionReport:
    """Return the last persisted predictions without re-running the model."""
    course = await course_service.get_course_for_user(db, course_id, user)

    rows = list(
        (
            await db.execute(
                select(StudentPrediction)
                .where(StudentPrediction.course_id == course_id)
                .order_by(StudentPrediction.student_id)
            )
        )
        .scalars()
        .all()
    )
    learning_gaps = await _learning_gaps(db, course_id, course.attainment_threshold)

    return StoredPredictionReport(
        course_id=course_id,
        threshold=course.attainment_threshold,
        predictions=[StoredPrediction.model_validate(row) for row in rows],
        learning_gaps=learning_gaps,
    )
