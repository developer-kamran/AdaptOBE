"""End-to-end attainment engine tests, including every section 8 edge case."""

from sqlalchemy import select

from app.models.attainment import AttainmentRecord
from app.services import attainment_service
from tests.conftest import auth_header


async def _records(db_session, course_id) -> list[AttainmentRecord]:
    result = await db_session.execute(
        select(AttainmentRecord).where(AttainmentRecord.course_id == course_id)
    )
    return list(result.scalars().all())


async def test_single_student_single_clo_exact_percentage(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    student = await make_student("solo")
    await enroll(student)

    assessment = await make_assessment(total_marks=20.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)
    q2 = await make_question(assessment.id, 2, 10.0, clo.id)

    # 8 + 7 = 15 out of 20 -> 75%
    await enter_scores(assessment.id, [(q1.id, student.id, 8.0), (q2.id, student.id, 7.0)])

    records = await _records(db_session, course.id)
    assert len(records) == 1
    assert records[0].attainment_percentage == 75.0


async def test_absent_student_scores_zero_and_stays_in_denominator(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    """Section 8: a student with no score row counts as 0.0 and is not dropped."""
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    present = await make_student("present")
    absent = await make_student("absent")
    await enroll(present, absent)

    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)

    # Only the present student has a score row at all.
    await enter_scores(assessment.id, [(q1.id, present.id, 10.0)])

    records = {r.student_id: r for r in await _records(db_session, course.id)}
    assert len(records) == 2
    assert records[present.id].attainment_percentage == 100.0
    assert records[absent.id].attainment_percentage == 0.0

    report = await attainment_service.build_course_report(db_session, course.id)
    # Denominator stays 2, so the average is 50 -- not the 100 you'd get by
    # silently excluding the absentee.
    assert report.clo_attainment[0].class_average == 50.0
    assert report.clo_attainment[0].student_count == 2


async def test_clo_with_no_tagged_questions_yields_zero_not_error(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    """Section 8: zero possible marks must return 0.00, never ZeroDivisionError."""
    tagged = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    untagged = await make_clo("CLO-2", "Recursion", "Explain recursive algorithms.")
    student = await make_student("zero")
    await enroll(student)

    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, tagged.id)
    await enter_scores(assessment.id, [(q1.id, student.id, 10.0)])

    records = {r.clo_id: r for r in await _records(db_session, course.id)}
    assert records[tagged.id].attainment_percentage == 100.0
    assert records[untagged.id].attainment_percentage == 0.0


async def test_questions_with_zero_marks_yield_zero(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    student = await make_student("zeromarks")
    await enroll(student)

    assessment = await make_assessment(total_marks=0.0)
    q1 = await make_question(assessment.id, 1, 0.0, clo.id)
    await enter_scores(assessment.id, [(q1.id, student.id, 0.0)])

    records = await _records(db_session, course.id)
    assert records[0].attainment_percentage == 0.0


async def test_course_with_no_enrolled_students_produces_no_records(
    db_session, course, make_clo, make_assessment, make_question
):
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    assessment = await make_assessment()
    await make_question(assessment.id, 1, 10.0, clo.id)

    count = await attainment_service.recalculate_course_attainment(db_session, course.id)
    assert count == 0
    assert await _records(db_session, course.id) == []

    report = await attainment_service.build_course_report(db_session, course.id)
    assert report.clo_attainment[0].class_average == 0.0


async def test_threshold_flagging_uses_class_average(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    """Section 8: is_achieved compares the CLASS AVERAGE against the threshold."""
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    high = await make_student("high")
    low = await make_student("low")
    await enroll(high, low)

    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)

    # 100 and 0 -> class average 50.0, exactly the default threshold.
    await enter_scores(assessment.id, [(q1.id, high.id, 10.0), (q1.id, low.id, 0.0)])

    records = await _records(db_session, course.id)
    # Every record shares the class-level verdict, including the student who scored 0.
    assert all(record.is_achieved for record in records)

    report = await attainment_service.build_course_report(db_session, course.id)
    assert report.clo_attainment[0].class_average == 50.0
    assert report.clo_attainment[0].is_achieved is True


async def test_below_threshold_flags_not_achieved(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    a = await make_student("a")
    b = await make_student("b")
    await enroll(a, b)

    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)
    # 4/10 and 5/10 -> average 45% < 50%
    await enter_scores(assessment.id, [(q1.id, a.id, 4.0), (q1.id, b.id, 5.0)])

    report = await attainment_service.build_course_report(db_session, course.id)
    assert report.clo_attainment[0].class_average == 45.0
    assert report.clo_attainment[0].is_achieved is False


async def test_custom_course_threshold_respected(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    course.attainment_threshold = 80.0
    await db_session.commit()

    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    student = await make_student("custom")
    await enroll(student)

    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)
    await enter_scores(assessment.id, [(q1.id, student.id, 7.0)])

    report = await attainment_service.build_course_report(db_session, course.id)
    assert report.threshold == 80.0
    assert report.clo_attainment[0].class_average == 70.0
    assert report.clo_attainment[0].is_achieved is False


async def test_marks_spread_across_two_assessments(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    """A CLO's attainment aggregates every tagged question across the course."""
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    student = await make_student("spread")
    await enroll(student)

    quiz = await make_assessment(title="Quiz", total_marks=10.0, weightage_percent=20.0)
    midterm = await make_assessment(title="Midterm", total_marks=30.0, weightage_percent=30.0)

    q1 = await make_question(quiz.id, 1, 10.0, clo.id)
    q2 = await make_question(midterm.id, 1, 30.0, clo.id)

    # 5/10 + 25/30 = 30/40 -> 75%
    await enter_scores(quiz.id, [(q1.id, student.id, 5.0)])
    await enter_scores(midterm.id, [(q2.id, student.id, 25.0)])

    records = await _records(db_session, course.id)
    assert records[0].attainment_percentage == 75.0


async def test_editing_a_score_triggers_recalculation(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    student = await make_student("edit")
    await enroll(student)

    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)

    await enter_scores(assessment.id, [(q1.id, student.id, 3.0)])
    assert (await _records(db_session, course.id))[0].attainment_percentage == 30.0

    # Re-entering the same (question, student) updates rather than duplicating.
    await enter_scores(assessment.id, [(q1.id, student.id, 9.0)])
    records = await _records(db_session, course.id)
    assert len(records) == 1
    assert records[0].attainment_percentage == 90.0


async def test_retagging_question_to_another_clo_recalculates(
    client, db_session, course, faculty, make_clo, make_student, enroll,
    make_assessment, make_question, enter_scores,
):
    """Section 8: editing a CLO tag must trigger recalculation."""
    clo_a = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    clo_b = await make_clo("CLO-2", "Recursion", "Explain recursive algorithms.")
    student = await make_student("retag")
    await enroll(student)

    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo_a.id)
    await enter_scores(assessment.id, [(q1.id, student.id, 10.0)])

    before = {r.clo_id: r.attainment_percentage for r in await _records(db_session, course.id)}
    assert before[clo_a.id] == 100.0
    assert before[clo_b.id] == 0.0

    resp = await client.patch(
        f"/api/v1/assessments/questions/{q1.id}",
        json={"clo_id": clo_b.id},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200

    after = {r.clo_id: r.attainment_percentage for r in await _records(db_session, course.id)}
    assert after[clo_a.id] == 0.0
    assert after[clo_b.id] == 100.0


async def test_deleting_question_recalculates(
    client, db_session, course, faculty, make_clo, make_student, enroll,
    make_assessment, make_question, enter_scores,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    student = await make_student("delq")
    await enroll(student)

    assessment = await make_assessment(total_marks=20.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)
    q2 = await make_question(assessment.id, 2, 10.0, clo.id)
    await enter_scores(assessment.id, [(q1.id, student.id, 10.0), (q2.id, student.id, 0.0)])

    assert (await _records(db_session, course.id))[0].attainment_percentage == 50.0

    resp = await client.delete(
        f"/api/v1/assessments/questions/{q2.id}", headers=auth_header(faculty)
    )
    assert resp.status_code == 204

    # Only the fully-correct question remains, so attainment climbs to 100%.
    assert (await _records(db_session, course.id))[0].attainment_percentage == 100.0


async def test_enrolling_new_student_moves_class_average(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    first = await make_student("first")
    await enroll(first)

    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)
    await enter_scores(assessment.id, [(q1.id, first.id, 10.0)])

    report = await attainment_service.build_course_report(db_session, course.id)
    assert report.clo_attainment[0].class_average == 100.0

    late = await make_student("late")
    await enroll(late)
    await attainment_service.recalculate_course_attainment(db_session, course.id)

    report = await attainment_service.build_course_report(db_session, course.id)
    assert report.clo_attainment[0].class_average == 50.0


async def test_plo_attainment_weighted_by_mapping_strength(
    db_session, course, faculty, make_clo, make_plo, make_student, enroll,
    make_assessment, make_question, enter_scores,
):
    from app.schemas.mapping import MappingConfirmRequest
    from app.services import mapping_service

    clo_strong = await make_clo("CLO-1", "Design", "Design software components.")
    clo_weak = await make_clo("CLO-2", "Testing", "Write unit tests for modules.")
    plo = await make_plo("PLO-1", "Engineering", "Apply engineering knowledge.")

    student = await make_student("plo")
    await enroll(student)

    assessment = await make_assessment(total_marks=20.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo_strong.id)
    q2 = await make_question(assessment.id, 2, 10.0, clo_weak.id)
    # CLO-1 -> 80%, CLO-2 -> 40%
    await enter_scores(assessment.id, [(q1.id, student.id, 8.0), (q2.id, student.id, 4.0)])

    await mapping_service.confirm_mapping(
        db_session,
        MappingConfirmRequest(clo_id=clo_strong.id, plo_id=plo.id, strength=3),
        faculty,
    )
    await mapping_service.confirm_mapping(
        db_session,
        MappingConfirmRequest(clo_id=clo_weak.id, plo_id=plo.id, strength=1),
        faculty,
    )

    report = await attainment_service.build_course_report(db_session, course.id)
    # (80*3 + 40*1) / 4 = 280/4 = 70.0
    assert report.plo_attainment[0].class_average == 70.0


async def test_unmapped_clos_produce_no_plo_rows(
    db_session, course, make_clo, make_student, enroll, make_assessment, make_question, enter_scores
):
    """Sum(Strength) = 0 for a course with no mappings: no PLO rows, no crash."""
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    student = await make_student("nomap")
    await enroll(student)

    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)
    await enter_scores(assessment.id, [(q1.id, student.id, 10.0)])

    report = await attainment_service.build_course_report(db_session, course.id)
    assert report.plo_attainment == []
    assert report.heatmap == []


async def test_recalculation_broadcasts_notification(
    db_session, course, make_clo, make_student, enroll
):
    from app.services import notifications

    received = []

    async def listener(event):
        received.append(event)

    notifications.subscribe(listener)
    try:
        await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
        student = await make_student("notify")
        await enroll(student)
        await attainment_service.recalculate_course_attainment(db_session, course.id)
    finally:
        notifications.unsubscribe(listener)

    assert any(event["type"] == "attainment.recalculated" for event in received)
    assert received[-1]["course_id"] == course.id


async def test_failing_subscriber_does_not_break_recalculation(
    db_session, course, make_clo, make_student, enroll
):
    from app.services import notifications

    async def bad_listener(event):
        raise RuntimeError("listener exploded")

    notifications.subscribe(bad_listener)
    try:
        await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
        student = await make_student("resilient")
        await enroll(student)
        count = await attainment_service.recalculate_course_attainment(db_session, course.id)
    finally:
        notifications.unsubscribe(bad_listener)

    assert count == 1
