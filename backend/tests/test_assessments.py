from app.models.user import UserRole
from tests.conftest import auth_header


async def test_create_assessment_requires_faculty_or_admin(client, make_user, course):
    student = await make_user("student.assess@adaptobe.edu", role=UserRole.student)
    resp = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course.id,
            "title": "Quiz 1",
            "type": "quiz",
            "total_marks": 10,
            "weightage_percent": 10,
        },
        headers=auth_header(student),
    )
    assert resp.status_code == 403


async def test_create_assessment_rejects_non_owner_faculty(client, make_user, course):
    other = await make_user("faculty.assess@adaptobe.edu", role=UserRole.faculty)
    resp = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course.id,
            "title": "Quiz 1",
            "type": "quiz",
            "total_marks": 10,
            "weightage_percent": 10,
        },
        headers=auth_header(other),
    )
    assert resp.status_code == 403


async def test_create_assessment_success(client, faculty, course):
    resp = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course.id,
            "title": "Midterm",
            "type": "midterm",
            "total_marks": 50,
            "weightage_percent": 30,
            "date": "2026-03-15",
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["type"] == "midterm"
    assert body["weightage_percent"] == 30


async def test_weightage_sum_capped_at_100(client, faculty, course):
    """Section 7: assessment creation validates that total weightage stays <= 100%."""
    for index, weight in enumerate([40, 40]):
        resp = await client.post(
            "/api/v1/assessments",
            json={
                "course_id": course.id,
                "title": f"Assessment {index}",
                "type": "quiz",
                "total_marks": 10,
                "weightage_percent": weight,
            },
            headers=auth_header(faculty),
        )
        assert resp.status_code == 201

    # 40 + 40 + 30 = 110 > 100
    resp = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course.id,
            "title": "Final",
            "type": "final",
            "total_marks": 10,
            "weightage_percent": 30,
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422
    assert "exceeds" in resp.json()["detail"]


async def test_weightage_exactly_100_is_allowed(client, faculty, course):
    resp = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course.id,
            "title": "Everything",
            "type": "final",
            "total_marks": 100,
            "weightage_percent": 100,
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201


async def test_update_weightage_respects_cap(client, faculty, course, make_assessment):
    first = await make_assessment(title="Quiz", weightage_percent=60.0)
    await make_assessment(title="Lab", weightage_percent=30.0)

    # Raising the first to 80 would total 110.
    resp = await client.patch(
        f"/api/v1/assessments/{first.id}",
        json={"weightage_percent": 80},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422

    # Lowering it is fine.
    resp = await client.patch(
        f"/api/v1/assessments/{first.id}",
        json={"weightage_percent": 50},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200


async def test_invalid_assessment_type_rejected(client, faculty, course):
    resp = await client.post(
        "/api/v1/assessments",
        json={
            "course_id": course.id,
            "title": "Bad Type",
            "type": "homework",
            "total_marks": 10,
            "weightage_percent": 10,
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422


async def test_question_must_be_tagged_with_own_course_clo(
    client, db_session, faculty, program, make_assessment, make_clo, course
):
    """A question cannot borrow a CLO from a different course."""
    from app.schemas.course import CourseCreate
    from app.services import course_service

    other_course = await course_service.create_course(
        db_session,
        CourseCreate(
            program_id=program.id, code="CS-OTHER", name="Other", credit_hours=3, semester=2
        ),
        faculty,
    )
    foreign_clo = await make_clo(
        "CLO-F", "Foreign", "Belongs to another course.", course_id=other_course.id
    )
    assessment = await make_assessment()

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/questions",
        json={"question_number": 1, "marks": 10, "clo_id": foreign_clo.id},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422


async def test_question_clo_not_found(client, faculty, make_assessment):
    assessment = await make_assessment()
    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/questions",
        json={"question_number": 1, "marks": 10, "clo_id": 999999},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 404


async def test_untagged_question_is_allowed(client, faculty, make_assessment):
    """Questions may be created before their CLO tag is decided."""
    assessment = await make_assessment()
    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/questions",
        json={"question_number": 1, "marks": 10},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201
    assert resp.json()["clo_id"] is None


async def test_bulk_scores_reject_marks_above_question_total(
    client, faculty, make_clo, make_student, enroll, make_assessment, make_question
):
    """Section 10: bulk score entry validates marks_obtained <= total marks."""
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    student = await make_student("overmarks")
    await enroll(student)
    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores",
        json={"scores": [{"question_id": q1.id, "student_id": student.id, "marks_obtained": 11}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422
    assert "exceeds" in resp.json()["detail"]


async def test_bulk_scores_reject_negative_marks(
    client, faculty, make_clo, make_student, enroll, make_assessment, make_question
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    student = await make_student("negative")
    await enroll(student)
    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores",
        json={"scores": [{"question_id": q1.id, "student_id": student.id, "marks_obtained": -1}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422


async def test_bulk_scores_reject_unenrolled_student(
    client, faculty, make_clo, make_student, make_assessment, make_question
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    outsider = await make_student("outsider")
    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores",
        json={"scores": [{"question_id": q1.id, "student_id": outsider.id, "marks_obtained": 5}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422
    assert "not enrolled" in resp.json()["detail"]


async def test_bulk_scores_reject_question_from_other_assessment(
    client, faculty, make_clo, make_student, enroll, make_assessment, make_question
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    student = await make_student("wrongq")
    await enroll(student)

    assessment_a = await make_assessment(title="A", weightage_percent=10.0, total_marks=10.0)
    assessment_b = await make_assessment(title="B", weightage_percent=10.0, total_marks=10.0)
    q_b = await make_question(assessment_b.id, 1, 10.0, clo.id)

    resp = await client.post(
        f"/api/v1/assessments/{assessment_a.id}/scores",
        json={"scores": [{"question_id": q_b.id, "student_id": student.id, "marks_obtained": 5}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 404


async def test_invalid_row_rejects_whole_batch(
    client, db_session, faculty, make_clo, make_student, enroll, make_assessment, make_question
):
    """One bad row must not leave a half-entered assessment behind."""
    from sqlalchemy import select

    from app.models.student_score import StudentScore

    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    good = await make_student("good")
    await enroll(good)
    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores",
        json={
            "scores": [
                {"question_id": q1.id, "student_id": good.id, "marks_obtained": 5},
                {"question_id": q1.id, "student_id": good.id, "marks_obtained": 99},
            ]
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422

    saved = await db_session.execute(select(StudentScore))
    assert list(saved.scalars().all()) == []


async def test_bulk_scores_success_reports_counts(
    client, faculty, make_clo, make_student, enroll, make_assessment, make_question
):
    clo = await make_clo("CLO-1", "Loops", "Write loops.")
    s1 = await make_student("s1")
    s2 = await make_student("s2")
    await enroll(s1, s2)
    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores",
        json={
            "scores": [
                {"question_id": q1.id, "student_id": s1.id, "marks_obtained": 8},
                {"question_id": q1.id, "student_id": s2.id, "marks_obtained": 6},
            ]
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201
    assert resp.json() == {"saved": 2, "recalculated_students": 2}


async def test_ai_question_tag_suggestion_ranks_relevant_clo_first(
    client, faculty, make_assessment, make_clo
):
    await make_clo("CLO-1", "Database Design", "Design relational database schemas and queries.")
    await make_clo("CLO-2", "Teamwork", "Collaborate effectively within a project team.")
    assessment = await make_assessment()

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/questions/suggest-tag",
        json={"text": "Design relational database schemas and queries."},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    suggestions = resp.json()["suggestions"]
    assert suggestions[0]["code"] == "CLO-1"
    assert suggestions[0]["similarity_score"] > suggestions[1]["similarity_score"]


async def test_enroll_rejects_non_student_role(client, faculty, course, make_user):
    another_faculty = await make_user("faculty.enroll@adaptobe.edu", role=UserRole.faculty)
    resp = await client.post(
        f"/api/v1/courses/{course.id}/enrollments",
        json={"student_ids": [another_faculty.id]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422
    assert "not a student" in resp.json()["detail"]


async def test_enroll_is_idempotent(client, faculty, course, make_student):
    student = await make_student("idem")
    payload = {"student_ids": [student.id]}

    first = await client.post(
        f"/api/v1/courses/{course.id}/enrollments", json=payload, headers=auth_header(faculty)
    )
    second = await client.post(
        f"/api/v1/courses/{course.id}/enrollments", json=payload, headers=auth_header(faculty)
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert len(second.json()) == 1


async def test_attainment_report_requires_course_access(client, make_user, course):
    other = await make_user("faculty.report@adaptobe.edu", role=UserRole.faculty)
    resp = await client.get(
        f"/api/v1/attainment/course/{course.id}", headers=auth_header(other)
    )
    assert resp.status_code == 403


async def test_attainment_report_rejects_students(client, make_user, course):
    student = await make_user("student.report@adaptobe.edu", role=UserRole.student)
    resp = await client.get(
        f"/api/v1/attainment/course/{course.id}", headers=auth_header(student)
    )
    assert resp.status_code == 403


async def test_attainment_report_shape(
    client, faculty, course, make_clo, make_plo, make_student, enroll,
    make_assessment, make_question, enter_scores,
):
    clo = await make_clo("CLO-1", "Loops", "Write loops and conditionals.")
    student = await make_student("shape")
    await enroll(student)
    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 10.0, clo.id)
    await enter_scores(assessment.id, [(q1.id, student.id, 7.0)])

    resp = await client.get(
        f"/api/v1/attainment/course/{course.id}", headers=auth_header(faculty)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["course_id"] == course.id
    assert body["threshold"] == 50.0
    assert body["student_count"] == 1
    assert body["clo_attainment"][0]["class_average"] == 70.0
    assert body["clo_attainment"][0]["is_achieved"] is True
