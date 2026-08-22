"""Attendance entry: service behavior, validation, and RBAC."""

from io import BytesIO

from openpyxl import Workbook

from app.services import attendance_service
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


def upload(content: bytes, filename: str = "attendance.xlsx"):
    return {
        "file": (
            filename,
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


async def test_set_and_list_attendance(
    db_session, course, make_student, enroll, client, faculty
):
    a = await make_student("att-a")
    b = await make_student("att-b")
    await enroll(a, b)

    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance",
        json={"entries": [
            {"student_id": a.id, "attendance_percentage": 80.0},
            {"student_id": b.id, "attendance_percentage": 55.0},
        ]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    assert resp.json()["saved"] == 2

    listing = await client.get(
        f"/api/v1/courses/{course.id}/attendance", headers=auth_header(faculty)
    )
    assert listing.status_code == 200
    by_student = {row["student_id"]: row["attendance_percentage"] for row in listing.json()}
    assert by_student == {a.id: 80.0, b.id: 55.0}


async def test_set_attendance_upserts(
    db_session, course, make_student, enroll, client, faculty
):
    student = await make_student("att-upsert")
    await enroll(student)

    await client.post(
        f"/api/v1/courses/{course.id}/attendance",
        json={"entries": [{"student_id": student.id, "attendance_percentage": 40.0}]},
        headers=auth_header(faculty),
    )
    await client.post(
        f"/api/v1/courses/{course.id}/attendance",
        json={"entries": [{"student_id": student.id, "attendance_percentage": 90.0}]},
        headers=auth_header(faculty),
    )

    mapping = await attendance_service.attendance_map(db_session, course.id)
    assert mapping[student.id] == 90.0  # updated, not duplicated


async def test_attendance_rejects_non_enrolled_student(
    db_session, course, make_student, client, faculty
):
    outsider = await make_student("att-outsider")  # never enrolled
    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance",
        json={"entries": [{"student_id": outsider.id, "attendance_percentage": 50.0}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422
    assert "not enrolled" in resp.json()["detail"].lower()


async def test_attendance_percentage_out_of_range_rejected(
    db_session, course, make_student, enroll, client, faculty
):
    student = await make_student("att-range")
    await enroll(student)
    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance",
        json={"entries": [{"student_id": student.id, "attendance_percentage": 150.0}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422  # schema Field(le=100)


async def test_attendance_is_faculty_only(
    db_session, course, make_student, client, sub_admin, super_admin
):
    student = await make_student("att-rbac")
    for actor in (sub_admin, super_admin, student):
        resp = await client.post(
            f"/api/v1/courses/{course.id}/attendance",
            json={"entries": [{"student_id": student.id, "attendance_percentage": 50.0}]},
            headers=auth_header(actor),
        )
        assert resp.status_code == 403
        listing = await client.get(
            f"/api/v1/courses/{course.id}/attendance", headers=auth_header(actor)
        )
        assert listing.status_code == 403


async def test_attendance_import_preview_matches_ready_student(
    client, faculty, course, make_student, enroll
):
    student = await make_student("att-import-ready")
    await enroll(student)

    content = build_xlsx(
        ["Full Name", "Father's Name", "Seat No", "Attendance %"],
        [[student.full_name, "Some Father", student.seat_no, "82.5"]],
    )
    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready_count"] == 1
    record = body["records"][0]
    assert record["status"] == "ready"
    assert record["matched_student_id"] == student.id


async def test_attendance_import_preview_flags_unenrolled_seat_no(client, faculty, course):
    content = build_xlsx(
        ["Full Name", "Father's Name", "Seat No", "Attendance %"],
        [["Ghost Student", "Ghost Father", "SEAT-GHOST", "70"]],
    )
    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["student_not_found_count"] == 1
    assert body["records"][0]["status"] == "student_not_found"


async def test_attendance_import_preview_rejects_out_of_range_percentage(
    client, faculty, course, make_student, enroll
):
    student = await make_student("att-import-range")
    await enroll(student)

    content = build_xlsx(
        ["Full Name", "Father's Name", "Seat No", "Attendance %"],
        [[student.full_name, "Some Father", student.seat_no, "150"]],
    )
    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["invalid_percentage_count"] == 1
    assert body["records"][0]["status"] == "invalid_percentage"


async def test_attendance_import_seat_no_valid_in_other_course_is_not_found(
    client, db_session, faculty, course, program, make_student
):
    """A seat_no that's a real, enrolled student elsewhere is still
    `student_not_found` for *this* course's import if they aren't enrolled
    in this specific course -- roster-scoped, not a global student lookup."""
    from app.schemas.course import CourseCreate
    from app.services import course_service, enrollment_service

    other_course = await course_service.create_course(
        db_session,
        CourseCreate(
            program_id=program.id, code="CS-902", name="Other Course", credit_hours=3, semester=2,
        ),
        faculty,
    )
    student = await make_student("att-import-othercourse")
    await enrollment_service.enroll_students(db_session, other_course.id, [student.id], faculty)

    content = build_xlsx(
        ["Full Name", "Father's Name", "Seat No", "Attendance %"],
        [[student.full_name, "Some Father", student.seat_no, "70"]],
    )
    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["student_not_found_count"] == 1
    assert body["records"][0]["status"] == "student_not_found"


async def test_attendance_import_writes_nothing_until_confirm(
    db_session, client, faculty, course, make_student, enroll
):
    student = await make_student("att-import-write")
    await enroll(student)

    content = build_xlsx(
        ["Full Name", "Father's Name", "Seat No", "Attendance %"],
        [[student.full_name, "Some Father", student.seat_no, "88"]],
    )
    await client.post(
        f"/api/v1/courses/{course.id}/attendance/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    mapping = await attendance_service.attendance_map(db_session, course.id)
    assert student.id not in mapping


async def test_attendance_import_confirm_saves_via_bulk_set_attendance(
    db_session, client, faculty, course, make_student, enroll
):
    student = await make_student("att-import-confirm")
    await enroll(student)

    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance/import/confirm",
        json={"entries": [{"student_id": student.id, "attendance_percentage": 91.0}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    assert resp.json()["saved"] == 1

    mapping = await attendance_service.attendance_map(db_session, course.id)
    assert mapping[student.id] == 91.0


async def test_attendance_import_requires_faculty_owner(client, make_user, course):
    other = await make_user("faculty.attimp@adaptobe.edu", role="faculty", employee_id="FAC-ATTIMP")
    content = build_xlsx(["Full Name", "Father's Name", "Seat No", "Attendance %"], [])
    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance/import/preview",
        files=upload(content),
        headers=auth_header(other),
    )
    assert resp.status_code == 403
