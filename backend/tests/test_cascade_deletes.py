"""Deleting a course or CLO must not fail on dangling foreign keys."""

from sqlalchemy import select

from app.models.clo import CLO
from app.models.mapping import CloPloMapping
from app.models.question import Question
from tests.conftest import auth_header


async def test_delete_course_removes_its_clos(client, db_session, faculty, course, make_clo):
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")

    resp = await client.delete(f"/api/v1/courses/{course.id}", headers=auth_header(faculty))
    assert resp.status_code == 204

    remaining = await db_session.execute(select(CLO).where(CLO.id == clo.id))
    assert remaining.scalar_one_or_none() is None


async def test_delete_course_with_full_obe_tree(
    client, db_session, faculty, course, make_clo, make_plo, make_student, enroll,
    make_assessment, make_question, enter_scores,
):
    """A course carrying CLOs, mappings, assessments, scores and attainment deletes cleanly."""
    from app.schemas.mapping import MappingConfirmRequest
    from app.services import mapping_service

    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    plo = await make_plo("PLO-1", "Knowledge", "Apply engineering knowledge.")
    await mapping_service.confirm_mapping(
        db_session, MappingConfirmRequest(clo_id=clo.id, plo_id=plo.id, strength=2), faculty
    )

    student = await make_student("cascade")
    await enroll(student)
    assessment = await make_assessment(total_marks=10.0)
    question = await make_question(assessment.id, 1, 10.0, clo.id)
    await enter_scores(assessment.id, [(question.id, student.id, 7.0)])

    resp = await client.delete(f"/api/v1/courses/{course.id}", headers=auth_header(faculty))
    assert resp.status_code == 204

    mappings = await db_session.execute(
        select(CloPloMapping).where(CloPloMapping.clo_id == clo.id)
    )
    assert mappings.scalar_one_or_none() is None


async def test_deleting_clo_untags_questions_but_keeps_them(
    client, db_session, faculty, course, make_clo, make_assessment, make_question
):
    """Removing a CLO must not destroy the exam questions that referenced it."""
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    assessment = await make_assessment(total_marks=10.0)
    question = await make_question(assessment.id, 1, 10.0, clo.id)

    resp = await client.delete(f"/api/v1/clos/{clo.id}", headers=auth_header(faculty))
    assert resp.status_code == 204

    # The SET NULL happened in the database, so the cached instance needs refreshing.
    await db_session.refresh(question)
    assert question.clo_id is None
    assert question.marks == 10.0


async def test_deleting_clo_removes_its_mappings(
    client, db_session, faculty, make_clo, make_plo
):
    from app.schemas.mapping import MappingConfirmRequest
    from app.services import mapping_service

    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    plo = await make_plo("PLO-1", "Knowledge", "Apply engineering knowledge.")
    mapping = await mapping_service.confirm_mapping(
        db_session, MappingConfirmRequest(clo_id=clo.id, plo_id=plo.id, strength=2), faculty
    )

    resp = await client.delete(f"/api/v1/clos/{clo.id}", headers=auth_header(faculty))
    assert resp.status_code == 204

    remaining = await db_session.execute(
        select(CloPloMapping).where(CloPloMapping.id == mapping.id)
    )
    assert remaining.scalar_one_or_none() is None


async def test_delete_assessment_removes_questions_and_scores(
    client, db_session, faculty, make_clo, make_student, enroll,
    make_assessment, make_question, enter_scores,
):
    from app.models.student_score import StudentScore

    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    student = await make_student("delassess")
    await enroll(student)
    assessment = await make_assessment(total_marks=10.0)
    question = await make_question(assessment.id, 1, 10.0, clo.id)
    await enter_scores(assessment.id, [(question.id, student.id, 7.0)])

    resp = await client.delete(
        f"/api/v1/assessments/{assessment.id}", headers=auth_header(faculty)
    )
    assert resp.status_code == 204

    questions = await db_session.execute(
        select(Question).where(Question.assessment_id == assessment.id)
    )
    assert list(questions.scalars().all()) == []

    scores = await db_session.execute(
        select(StudentScore).where(StudentScore.question_id == question.id)
    )
    assert list(scores.scalars().all()) == []
