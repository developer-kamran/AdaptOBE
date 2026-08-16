"""Module 6 student portal: progress, score history, adaptive quiz, RBAC."""

from app.schemas.question import QuestionCreate
from app.models.question import QuestionType
from app.services import question_service
from tests.conftest import auth_header


async def _typed_question(
    db_session, faculty, assessment_id, number, qtype, type_data, clo_id, marks=1.0
):
    return await question_service.create_question(
        db_session,
        assessment_id,
        QuestionCreate(
            question_number=number,
            marks=marks,
            clo_id=clo_id,
            text=f"Q{number}",
            question_type=qtype,
            type_data=type_data,
        ),
        faculty,
    )


async def test_progress_shows_own_courses_and_weak_flags(
    db_session, course, make_clo, make_student, enroll, make_assessment,
    make_question, enter_scores, client,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    student = await make_student("prog")
    await enroll(student)
    assessment = await make_assessment(total_marks=10.0)
    q = await make_question(assessment.id, 1, 10.0, clo.id)
    await enter_scores(assessment.id, [(q.id, student.id, 3.0)])  # 30% -> weak (<50)

    resp = await client.get("/api/v1/student/progress", headers=auth_header(student))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["courses"]) == 1
    course_progress = body["courses"][0]
    assert course_progress["course_id"] == course.id
    clo_row = course_progress["clo_progress"][0]
    assert clo_row["attainment_percentage"] == 30.0
    assert clo_row["is_weak"] is True
    assert course_progress["weak_clo_count"] == 1


async def test_progress_is_scoped_to_the_authenticated_student(
    db_session, course, make_clo, make_student, enroll, make_assessment,
    make_question, enter_scores, client,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    enrolled = await make_student("mine")
    other = await make_student("theirs")  # never enrolled anywhere
    await enroll(enrolled)
    assessment = await make_assessment(total_marks=10.0)
    q = await make_question(assessment.id, 1, 10.0, clo.id)
    await enter_scores(assessment.id, [(q.id, enrolled.id, 8.0)])

    # The other student, with no enrolments, sees an empty progress report --
    # never the enrolled student's data.
    resp = await client.get("/api/v1/student/progress", headers=auth_header(other))
    assert resp.status_code == 200
    assert resp.json()["courses"] == []


async def test_score_history_requires_enrolment(
    db_session, course, make_student, client,
):
    outsider = await make_student("no-enroll")
    resp = await client.get(
        f"/api/v1/student/courses/{course.id}/scores", headers=auth_header(outsider)
    )
    assert resp.status_code == 403


async def test_adaptive_quiz_only_serves_auto_gradable_and_strips_answers(
    db_session, course, make_clo, make_student, enroll, make_assessment, faculty, client,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    student = await make_student("quiz")
    await enroll(student)
    assessment = await make_assessment(total_marks=10.0)

    await _typed_question(
        db_session, faculty, assessment.id, 1, QuestionType.mcq,
        {"options": [{"label": "A", "text": "one"}, {"label": "B", "text": "two"}], "correct_option": "B"},
        clo.id,
    )
    await _typed_question(
        db_session, faculty, assessment.id, 2, QuestionType.true_false,
        {"correct_answer": True}, clo.id,
    )
    # A free-form question that must NOT appear in the quiz.
    await _typed_question(
        db_session, faculty, assessment.id, 3, QuestionType.question, None, clo.id,
    )

    resp = await client.get(
        f"/api/v1/student/courses/{course.id}/adaptive-quiz", headers=auth_header(student)
    )
    assert resp.status_code == 200
    quiz = resp.json()
    types = {q["question_type"] for q in quiz["questions"]}
    assert types <= {"mcq", "true_false"}  # never the free-form "question"
    assert "question" not in types

    # No correct answer leaks: serialized questions have no answer fields, and
    # MCQ options carry only label/text.
    serialized = str(quiz)
    assert "correct_option" not in serialized
    assert "correct_answer" not in serialized


async def test_adaptive_quiz_grading_and_focus(
    db_session, course, make_clo, make_student, enroll, make_assessment, faculty, client,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    student = await make_student("grade")
    await enroll(student)
    assessment = await make_assessment(total_marks=10.0)

    mcq = await _typed_question(
        db_session, faculty, assessment.id, 1, QuestionType.mcq,
        {"options": [{"label": "A"}, {"label": "B"}], "correct_option": "B"}, clo.id,
    )
    tf = await _typed_question(
        db_session, faculty, assessment.id, 2, QuestionType.true_false,
        {"correct_answer": True}, clo.id,
    )

    resp = await client.post(
        f"/api/v1/student/courses/{course.id}/adaptive-quiz/submit",
        json={"answers": [
            {"question_id": mcq.id, "answer": "B"},   # correct
            {"question_id": tf.id, "answer": False},  # wrong
        ]},
        headers=auth_header(student),
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["total"] == 2
    assert result["correct"] == 1
    assert result["score_percentage"] == 50.0
    assert "CLO-1" in result["focus_clos"]  # got a CLO-1 question wrong


async def test_student_endpoints_are_student_only(
    db_session, course, client, faculty, sub_admin, super_admin,
):
    for actor in (faculty, sub_admin, super_admin):
        progress = await client.get("/api/v1/student/progress", headers=auth_header(actor))
        assert progress.status_code == 403
        quiz = await client.get(
            f"/api/v1/student/courses/{course.id}/adaptive-quiz", headers=auth_header(actor)
        )
        assert quiz.status_code == 403
