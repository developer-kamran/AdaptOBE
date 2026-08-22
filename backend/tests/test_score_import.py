"""Score-sheet import: upload -> preview (writes nothing) -> confirm (delegates
to the same `score_service.bulk_enter_scores` manual entry uses)."""

from io import BytesIO

from openpyxl import Workbook
from sqlalchemy import select

from app.models.student_score import StudentScore
from tests.conftest import auth_header


def build_xlsx(headers: list[str], rows: list[list]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def upload(content: bytes, filename: str = "scores.xlsx"):
    return {
        "file": (
            filename,
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


async def test_preview_matches_ready_student_with_valid_marks(
    client, faculty, make_assessment, make_question, make_student, enroll
):
    assessment = await make_assessment(total_marks=10.0)
    q1 = await make_question(assessment.id, 1, 5.0, text="Q1 text")
    q2 = await make_question(assessment.id, 2, 5.0, text="Q2 text")
    student = await make_student("scoreimp1")
    await enroll(student)

    content = build_xlsx(["Seat No", "Q1", "Q2"], [[student.seat_no, "4", "5"]])
    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready_count"] == 1
    record = body["records"][0]
    assert record["status"] == "ready"
    assert record["matched_student_id"] == student.id
    assert record["marks"] == {str(q1.id): 4.0, str(q2.id): 5.0}


async def test_preview_flags_student_not_found(client, faculty, make_assessment, make_question):
    assessment = await make_assessment(total_marks=5.0)
    await make_question(assessment.id, 1, 5.0, text="Q1")

    content = build_xlsx(["Seat No", "Q1"], [["SEAT-GHOST", "3"]])
    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["ready_count"] == 0
    assert body["student_not_found_count"] == 1
    assert body["records"][0]["status"] == "student_not_found"


async def test_preview_flags_duplicate_seat_no_in_file(
    client, faculty, make_assessment, make_question, make_student, enroll
):
    assessment = await make_assessment(total_marks=5.0)
    await make_question(assessment.id, 1, 5.0, text="Q1")
    student = await make_student("scoreimpdup")
    await enroll(student)

    content = build_xlsx(
        ["Seat No", "Q1"], [[student.seat_no, "3"], [student.seat_no, "4"]]
    )
    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["duplicate_count"] == 1
    statuses = [r["status"] for r in body["records"]]
    assert "duplicate_in_file" in statuses


async def test_preview_rejects_marks_exceeding_question_max(
    client, faculty, make_assessment, make_question, make_student, enroll
):
    assessment = await make_assessment(total_marks=5.0)
    q1 = await make_question(assessment.id, 1, 5.0, text="Q1")
    student = await make_student("scoreimpover")
    await enroll(student)

    content = build_xlsx(["Seat No", "Q1"], [[student.seat_no, "99"]])
    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    body = resp.json()
    record = body["records"][0]
    assert record["status"] == "no_marks"
    assert str(q1.id) in record["rejected_marks"]


async def test_preview_positional_fallback_when_headers_dont_match_aliases(
    client, faculty, make_assessment, make_question, make_student, enroll
):
    assessment = await make_assessment(total_marks=10.0)
    await make_question(assessment.id, 1, 5.0, text="Q1")
    await make_question(assessment.id, 2, 5.0, text="Q2")
    student = await make_student("scoreimppos")
    await enroll(student)

    content = build_xlsx(["Seat No", "Part A", "Part B"], [[student.seat_no, "5", "4"]])
    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["ready_count"] == 1
    columns = {c["question_number"]: c["matched_by"] for c in body["detected_question_columns"]}
    assert columns[1] == "position"
    assert columns[2] == "position"


async def test_preview_writes_nothing(
    client, db_session, faculty, make_assessment, make_question, make_student, enroll
):
    assessment = await make_assessment(total_marks=5.0)
    q1 = await make_question(assessment.id, 1, 5.0, text="Q1")
    student = await make_student("scoreimpwrite")
    await enroll(student)

    content = build_xlsx(["Seat No", "Q1"], [[student.seat_no, "4"]])
    await client.post(
        f"/api/v1/assessments/{assessment.id}/scores/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )

    # Scoped to this test's own question -- the dev DB may already carry
    # unrelated real StudentScore rows (see HANDOFF.md's test-isolation note).
    scores = (
        await db_session.execute(select(StudentScore).where(StudentScore.question_id == q1.id))
    ).scalars().all()
    assert scores == []


async def test_confirm_saves_scores_and_recalculates(
    client, db_session, faculty, make_assessment, make_question, make_student, enroll
):
    assessment = await make_assessment(total_marks=5.0)
    q1 = await make_question(assessment.id, 1, 5.0, text="Q1")
    student = await make_student("scoreimpconfirm")
    await enroll(student)

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores/import/confirm",
        json={"scores": [{"question_id": q1.id, "student_id": student.id, "marks_obtained": 4.0}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["saved"] == 1
    # recalculated_students is legitimately 0 here -- this course has no CLOs,
    # so there's nothing for the attainment engine to recompute (same rule
    # `recalculate_course_attainment` applies everywhere else).

    stored = (
        await db_session.execute(
            select(StudentScore).where(
                StudentScore.question_id == q1.id, StudentScore.student_id == student.id
            )
        )
    ).scalar_one()
    assert stored.marks_obtained == 4.0


async def test_confirm_still_rejects_marks_exceeding_question_max(
    client, faculty, make_assessment, make_question, make_student, enroll
):
    """Defense in depth: even if a row were somehow marked ready client-side,
    the server-side bulk_enter_scores validation still applies at confirm."""
    assessment = await make_assessment(total_marks=5.0)
    q1 = await make_question(assessment.id, 1, 5.0, text="Q1")
    student = await make_student("scoreimpguard")
    await enroll(student)

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores/import/confirm",
        json={"scores": [{"question_id": q1.id, "student_id": student.id, "marks_obtained": 99.0}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422


async def test_score_import_requires_faculty_owner(client, make_user, make_assessment):
    other = await make_user("faculty.scoreimp@adaptobe.edu", role="faculty", employee_id="FAC-SCOREIMP")
    assessment = await make_assessment(total_marks=5.0)
    content = build_xlsx(["Seat No", "Q1"], [["SEAT-X", "1"]])
    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/scores/import/preview",
        files=upload(content),
        headers=auth_header(other),
    )
    assert resp.status_code == 403
