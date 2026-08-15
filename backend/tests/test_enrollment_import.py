"""Course-enrollment roster import: matching an uploaded file to *existing*
student accounts and enrolling them -- distinct from the admin bulk import
in test_student_import.py, which creates accounts. See
app/services/enrollment_import_service.py for the preview/confirm split.

Also covers the programme + batch-year based student filtering
(`GET /students?course_id=`, and `&backlog=true` for the opposite rule) these
features share -- see `app.core.institution.expected_seat_no_prefix` /
`is_backlog_batch_year`.
"""

from io import BytesIO

from openpyxl import Workbook

from app.models.user import UserRole
from tests.conftest import auth_header

HEADERS = ["Full Name", "Father's Name", "Enrollment No", "Seat No", "Eligible"]


def build_xlsx(rows: list[list[str]], headers: list[str] | None = None) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers if headers is not None else HEADERS)
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def upload(content: bytes, filename: str = "roster.xlsx"):
    return {
        "file": (
            filename,
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


async def test_preview_matches_existing_student_as_ready(client, faculty, course, make_student):
    student = await make_student("import1")
    content = build_xlsx([[student.full_name, "Some Father", student.enrollment_no, student.seat_no, "Yes"]])

    resp = await client.post(
        f"/api/v1/courses/{course.id}/enrollments/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready_count"] == 1
    record = body["records"][0]
    assert record["status"] == "ready"
    assert record["matched_student_id"] == student.id


async def test_preview_not_found_when_no_matching_account(client, faculty, course):
    content = build_xlsx([["Ghost Student", "Ghost Father", "ENR-NOPE", "SEAT-NOPE", "Yes"]])

    resp = await client.post(
        f"/api/v1/courses/{course.id}/enrollments/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["not_found_count"] == 1
    assert body["records"][0]["status"] == "not_found"


async def test_preview_ineligible_row_is_excluded_from_ready(client, faculty, course, make_student):
    student = await make_student("import2")
    content = build_xlsx([[student.full_name, "F", student.enrollment_no, student.seat_no, "No"]])

    resp = await client.post(
        f"/api/v1/courses/{course.id}/enrollments/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["ready_count"] == 0
    assert body["ineligible_count"] == 1
    assert body["records"][0]["status"] == "ineligible"


async def test_preview_flags_already_enrolled_student(client, faculty, course, make_student, enroll):
    student = await make_student("import3")
    await enroll(student)
    content = build_xlsx([[student.full_name, "F", student.enrollment_no, student.seat_no, "Yes"]])

    resp = await client.post(
        f"/api/v1/courses/{course.id}/enrollments/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["already_enrolled_count"] == 1
    assert body["ready_count"] == 0
    assert body["records"][0]["status"] == "already_enrolled"


async def test_preview_flags_duplicate_rows_in_file(client, faculty, course, make_student):
    student = await make_student("import4")
    content = build_xlsx(
        [
            [student.full_name, "F", student.enrollment_no, student.seat_no, "Yes"],
            [student.full_name, "F", student.enrollment_no, student.seat_no, "Yes"],
        ]
    )

    resp = await client.post(
        f"/api/v1/courses/{course.id}/enrollments/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["duplicate_count"] == 1
    assert body["ready_count"] == 1


async def _get_program_by_code(db_session, code: str):
    """`programs.code` is globally unique institutional data seeded by
    `seed_ubit_data.py` (see app/core/institution.py) -- these tests need the
    *real* BSSE/BSCS codes to exercise `SEAT_NO_PROGRAM_CODES`, so they look
    the row up rather than creating a colliding duplicate."""
    from sqlalchemy import select

    from app.models.program import Program

    return (
        await db_session.execute(select(Program).where(Program.code == code))
    ).scalar_one()


async def test_preview_flags_wrong_programme(client, db_session, faculty):
    """A course scoped to BSSE should not offer a BSCS student as enrollable."""
    from app.schemas.course import CourseCreate
    from app.services import course_service

    bsse_program = await _get_program_by_code(db_session, "BSSE")
    bsse_course = await course_service.create_course(
        db_session,
        CourseCreate(
            program_id=bsse_program.id, code="SE-100", name="Intro to SE", credit_hours=3, semester=1
        ),
        faculty,
    )

    from app.schemas.user import UserCreate
    from app.services import auth_service

    await auth_service.register_user(
        db_session,
        UserCreate(
            email="student.wrongprog@adaptobe.edu",
            password="password123",
            full_name="Wrong Programme Student",
            role=UserRole.student,
            enrollment_no="ENR-WRONGPROG",
            seat_no="B221100-9999",  # BSCS prefix, not BSSE
            father_name="Father Wrongprog",
        ),
    )

    content = build_xlsx(
        [["Wrong Programme Student", "Father Wrongprog", "ENR-WRONGPROG", "B221100-9999", "Yes"]]
    )
    resp = await client.post(
        f"/api/v1/courses/{bsse_course.id}/enrollments/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["wrong_programme_count"] == 1
    assert body["records"][0]["status"] == "wrong_programme"


async def test_confirm_enrolls_only_ready_students(client, faculty, course, make_student):
    ready_student = await make_student("import5")
    content = build_xlsx(
        [[ready_student.full_name, "F", ready_student.enrollment_no, ready_student.seat_no, "Yes"]]
    )

    preview = await client.post(
        f"/api/v1/courses/{course.id}/enrollments/import/preview",
        files=upload(content),
        headers=auth_header(faculty),
    )
    ready_ids = [
        r["matched_student_id"] for r in preview.json()["records"] if r["status"] == "ready"
    ]
    assert ready_ids == [ready_student.id]

    resp = await client.post(
        f"/api/v1/courses/{course.id}/enrollments/import/confirm",
        json={"student_ids": ready_ids},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201

    listing = await client.get(
        f"/api/v1/courses/{course.id}/enrollments", headers=auth_header(faculty)
    )
    assert ready_student.id in [e["student_id"] for e in listing.json()]


async def test_preview_rejects_non_owner_faculty(client, make_user, course):
    other = await make_user(
        "faculty.importother@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-IMPORTOTHER"
    )
    content = build_xlsx([["Someone", "Father", "ENR-X", "SEAT-X", "Yes"]])
    resp = await client.post(
        f"/api/v1/courses/{course.id}/enrollments/import/preview",
        files=upload(content),
        headers=auth_header(other),
    )
    assert resp.status_code == 403


# --- Programme + batch-year based student filtering (item 5) ----------------


async def _make_bsse_course(db_session, faculty, semester: int):
    from app.schemas.course import CourseCreate
    from app.services import course_service

    bsse_program = await _get_program_by_code(db_session, "BSSE")
    return await course_service.create_course(
        db_session,
        CourseCreate(
            program_id=bsse_program.id,
            code=f"SE-SEM{semester}",
            name="Seat-No Filtering Course",
            credit_hours=3,
            semester=semester,
        ),
        faculty,
    )


async def _dept_faculty(make_user, department, suffix: str):
    """The shared `faculty` fixture has no `dept_id`, but `GET /students` is
    now department-scoped for faculty too -- these tests need a faculty
    account in the *same* department as the students they create."""
    return await make_user(
        f"faculty.{suffix}@adaptobe.edu",
        role=UserRole.faculty,
        dept_id=department.id,
        employee_id=f"FAC-{suffix.upper()}",
    )


async def test_list_students_course_filter_excludes_other_programme(
    client, db_session, make_user, department
):
    from app.core.institution import expected_seat_no_prefix
    from app.schemas.user import UserCreate
    from app.services import auth_service

    faculty = await _dept_faculty(make_user, department, "coursefilter")
    course = await _make_bsse_course(db_session, faculty, semester=4)
    current_batch_prefix = expected_seat_no_prefix("BSSE", 4)

    bsse_student = await auth_service.register_user(
        db_session,
        UserCreate(
            email="student.bsseonly@adaptobe.edu",
            password="password123",
            full_name="BSSE Student",
            role=UserRole.student,
            enrollment_no="ENR-BSSEONLY",
            seat_no=f"{current_batch_prefix}-0001",
            father_name="Father BSSE",
            dept_id=department.id,
        ),
    )
    bscs_student = await auth_service.register_user(
        db_session,
        UserCreate(
            email="student.bcsonly@adaptobe.edu",
            password="password123",
            full_name="BSCS Student",
            role=UserRole.student,
            enrollment_no="ENR-BSCSONLY",
            seat_no=expected_seat_no_prefix("BSCS", 4) + "-0001",
            father_name="Father BSCS",
            dept_id=department.id,
        ),
    )

    resp = await client.get(f"/api/v1/students?course_id={course.id}", headers=auth_header(faculty))
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert bsse_student.id in ids
    assert bscs_student.id not in ids


async def test_list_students_course_filter_excludes_wrong_batch_year(
    client, db_session, make_user, department
):
    """Same programme is not enough -- a BSSE student from the wrong batch
    year must not appear as a normal-enrollment candidate either."""
    from app.core.institution import expected_seat_no_prefix
    from app.schemas.user import UserCreate
    from app.services import auth_service

    faculty = await _dept_faculty(make_user, department, "wrongbatch")
    course = await _make_bsse_course(db_session, faculty, semester=4)
    current_batch_prefix = expected_seat_no_prefix("BSSE", 4)
    older_batch_prefix = expected_seat_no_prefix("BSSE", 8)  # further back

    current_student = await auth_service.register_user(
        db_session,
        UserCreate(
            email="student.currentbatch@adaptobe.edu",
            password="password123",
            full_name="Current Batch Student",
            role=UserRole.student,
            enrollment_no="ENR-CURRENTBATCH",
            seat_no=f"{current_batch_prefix}-0002",
            father_name="Father Current",
            dept_id=department.id,
        ),
    )
    older_student = await auth_service.register_user(
        db_session,
        UserCreate(
            email="student.olderbatch@adaptobe.edu",
            password="password123",
            full_name="Older Batch Student",
            role=UserRole.student,
            enrollment_no="ENR-OLDERBATCH",
            seat_no=f"{older_batch_prefix}-0003",
            father_name="Father Older",
            dept_id=department.id,
        ),
    )

    resp = await client.get(f"/api/v1/students?course_id={course.id}", headers=auth_header(faculty))
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert current_student.id in ids
    assert older_student.id not in ids


async def test_list_students_backlog_filter_returns_only_earlier_batches(
    client, db_session, make_user, department
):
    """backlog=true flips the rule: any programme, but strictly earlier than
    the course's current batch year."""
    from app.core.institution import expected_seat_no_prefix
    from app.schemas.user import UserCreate
    from app.services import auth_service

    faculty = await _dept_faculty(make_user, department, "backlogfilter")
    course = await _make_bsse_course(db_session, faculty, semester=4)
    current_batch_prefix = expected_seat_no_prefix("BSSE", 4)
    older_bsse_prefix = expected_seat_no_prefix("BSSE", 8)
    older_bscs_prefix = expected_seat_no_prefix("BSCS", 8)  # different programme, still earlier

    current_student = await auth_service.register_user(
        db_session,
        UserCreate(
            email="student.notbacklog@adaptobe.edu",
            password="password123",
            full_name="Not Backlog",
            role=UserRole.student,
            enrollment_no="ENR-NOTBACKLOG",
            seat_no=f"{current_batch_prefix}-0004",
            father_name="Father Notbacklog",
            dept_id=department.id,
        ),
    )
    backlog_bsse_student = await auth_service.register_user(
        db_session,
        UserCreate(
            email="student.backlogbsse@adaptobe.edu",
            password="password123",
            full_name="Backlog BSSE",
            role=UserRole.student,
            enrollment_no="ENR-BACKLOGBSSE",
            seat_no=f"{older_bsse_prefix}-0005",
            father_name="Father Backlogbsse",
            dept_id=department.id,
        ),
    )
    backlog_bscs_student = await auth_service.register_user(
        db_session,
        UserCreate(
            email="student.backlogbscs@adaptobe.edu",
            password="password123",
            full_name="Backlog BSCS",
            role=UserRole.student,
            enrollment_no="ENR-BACKLOGBSCS",
            seat_no=f"{older_bscs_prefix}-0006",
            father_name="Father Backlogbscs",
            dept_id=department.id,
        ),
    )

    resp = await client.get(
        f"/api/v1/students?course_id={course.id}&backlog=true", headers=auth_header(faculty)
    )
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert current_student.id not in ids
    assert backlog_bsse_student.id in ids
    assert backlog_bscs_student.id in ids  # backlog is not programme-restricted
