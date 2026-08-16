"""Module 5 risk prediction: features, SHAP payload, the >=5 gate, RBAC, gaps.

These tests train the real XGBoost model once (cached in-process on first
predict), so the first case here is a little slower than a pure DB test.
"""

from app.services import attendance_service, risk_math
from app.schemas.attendance import AttendanceEntry, BulkAttendanceRequest
from tests.conftest import auth_header


async def _grade(
    course, clo, make_assessment, make_question, enter_scores, marks_by_student, *,
    total=10.0, n=5,
):
    """Create `n` CLO-tagged quiz assessments and score each student in all of
    them, so every student ends up with `n` assessment records."""
    for i in range(n):
        assessment = await make_assessment(
            title=f"Quiz {i}", total_marks=total, weightage_percent=1.0
        )
        question = await make_question(assessment.id, 1, total, clo.id)
        await enter_scores(
            assessment.id,
            [(question.id, sid, marks) for sid, marks in marks_by_student.items()],
        )


async def _set_attendance(db_session, course, faculty, mapping):
    await attendance_service.bulk_set_attendance(
        db_session,
        course.id,
        BulkAttendanceRequest(
            entries=[AttendanceEntry(student_id=s, attendance_percentage=p) for s, p in mapping.items()]
        ),
        faculty,
    )


async def test_prediction_report_and_shap_shape(
    db_session, course, make_clo, make_student, enroll, make_assessment,
    make_question, enter_scores, client, faculty,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    student = await make_student("risk-solo")
    await enroll(student)
    await _grade(course, clo, make_assessment, make_question, enter_scores, {student.id: 6.0})
    await _set_attendance(db_session, course, faculty, {student.id: 70.0})

    resp = await client.post(
        f"/api/v1/ml/predict-risk/{course.id}", headers=auth_header(faculty)
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["course_id"] == course.id
    assert body["predicted_count"] == 1
    assert body["skipped"] == []

    pred = body["predictions"][0]
    assert pred["student_id"] == student.id
    assert pred["risk_level"] in {"low", "medium", "high"}
    assert 0.0 <= pred["confidence_score"] <= 1.0
    assert set(pred["features"]) == set(risk_math.FEATURE_NAMES)
    # Attendance we entered flowed into the feature vector.
    assert pred["features"]["attendance_percentage"] == 70.0

    shap = pred["shap_explanation"]
    assert set(shap) == {"base_value", "predicted_risk", "confidence", "feature_contributions"}
    assert shap["predicted_risk"] == pred["risk_level"]
    assert len(shap["feature_contributions"]) == len(risk_math.FEATURE_NAMES)
    for contribution in shap["feature_contributions"]:
        assert set(contribution) == {"feature", "value", "shap_value", "impact"}
        assert contribution["impact"] in {"increased_risk", "decreased_risk"}


async def test_prediction_is_persisted_and_readable(
    db_session, course, make_clo, make_student, enroll, make_assessment,
    make_question, enter_scores, client, faculty,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    student = await make_student("risk-persist")
    await enroll(student)
    await _grade(course, clo, make_assessment, make_question, enter_scores, {student.id: 5.0})

    await client.post(f"/api/v1/ml/predict-risk/{course.id}", headers=auth_header(faculty))

    stored = await client.get(
        f"/api/v1/ml/predict-risk/{course.id}", headers=auth_header(faculty)
    )
    assert stored.status_code == 200
    body = stored.json()
    assert len(body["predictions"]) == 1
    assert body["predictions"][0]["student_id"] == student.id
    assert "shap_explanation" in body["predictions"][0]


async def test_student_with_too_few_records_is_skipped(
    db_session, course, make_clo, make_student, enroll, make_assessment,
    make_question, enter_scores, client, faculty,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    student = await make_student("risk-thin")
    await enroll(student)
    # Only 2 assessment records -- below the required 5.
    await _grade(
        course, clo, make_assessment, make_question, enter_scores, {student.id: 5.0}, n=2
    )

    resp = await client.post(
        f"/api/v1/ml/predict-risk/{course.id}", headers=auth_header(faculty)
    )
    body = resp.json()
    assert body["predicted_count"] == 0
    assert len(body["skipped"]) == 1
    skipped = body["skipped"][0]
    assert skipped["student_id"] == student.id
    assert skipped["reason"] == "insufficient_assessment_records"
    assert skipped["assessment_records"] == 2


async def test_predict_with_no_enrolled_students(db_session, course, client, faculty):
    resp = await client.post(
        f"/api/v1/ml/predict-risk/{course.id}", headers=auth_header(faculty)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["predictions"] == []
    assert body["skipped"] == []


async def test_strong_and_weak_students_rank_as_expected(
    db_session, course, make_clo, make_student, enroll, make_assessment,
    make_question, enter_scores, client, faculty,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    strong = await make_student("risk-strong")
    weak = await make_student("risk-weak")
    await enroll(strong, weak)
    await _grade(
        course, clo, make_assessment, make_question, enter_scores,
        {strong.id: 10.0, weak.id: 1.0},
    )
    await _set_attendance(db_session, course, faculty, {strong.id: 100.0, weak.id: 10.0})

    resp = await client.post(
        f"/api/v1/ml/predict-risk/{course.id}", headers=auth_header(faculty)
    )
    preds = {p["student_id"]: p for p in resp.json()["predictions"]}
    assert preds[strong.id]["predicted_score"] > preds[weak.id]["predicted_score"]
    assert preds[strong.id]["risk_level"] == "low"
    assert preds[weak.id]["risk_level"] == "high"


async def test_learning_gap_detection_flags_below_threshold_clo(
    db_session, course, make_clo, make_student, enroll, make_assessment,
    make_question, enter_scores, client, faculty,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    student = await make_student("risk-gap")
    await enroll(student)
    # Score 2/10 = 20% class average, below the default 50% threshold.
    await _grade(course, clo, make_assessment, make_question, enter_scores, {student.id: 2.0})

    resp = await client.post(
        f"/api/v1/ml/predict-risk/{course.id}", headers=auth_header(faculty)
    )
    gaps = resp.json()["learning_gaps"]
    assert any(gap["clo_id"] == clo.id for gap in gaps)
    gap = next(g for g in gaps if g["clo_id"] == clo.id)
    assert gap["class_average"] < gap["threshold"]


async def test_predict_risk_is_faculty_only(
    db_session, course, make_student, client, sub_admin, super_admin
):
    student = await make_student("risk-rbac")
    for actor in (sub_admin, super_admin, student):
        post = await client.post(
            f"/api/v1/ml/predict-risk/{course.id}", headers=auth_header(actor)
        )
        assert post.status_code == 403
        get = await client.get(
            f"/api/v1/ml/predict-risk/{course.id}", headers=auth_header(actor)
        )
        assert get.status_code == 403
