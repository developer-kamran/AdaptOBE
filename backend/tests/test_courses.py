from app.models.user import UserRole
from app.schemas.department import DepartmentCreate
from app.services import department_service
from tests.conftest import auth_header


async def test_create_course_requires_faculty_or_sub_admin(client, make_user, program):
    student = await make_user(
        "student.course@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-COURSE",
        seat_no="SEAT-COURSE",
        father_name="Father Course",
    )
    resp = await client.post(
        "/api/v1/courses",
        json={
            "program_id": program.id,
            "code": "CS-999",
            "name": "Blocked Course",
            "credit_hours": 3,
            "semester": 1,
        },
        headers=auth_header(student),
    )
    assert resp.status_code == 403


async def test_create_course_assigns_creator_as_owner(client, make_user, program):
    faculty = await make_user(
        "faculty.create@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-CREATE"
    )
    resp = await client.post(
        "/api/v1/courses",
        json={
            "program_id": program.id,
            "code": "CS-201",
            "name": "Data Structures",
            "credit_hours": 4,
            "semester": 3,
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201
    assert resp.json()["owner_faculty_id"] == faculty.id


async def test_create_course_duplicate_code_conflict(client, faculty, program, course):
    resp = await client.post(
        "/api/v1/courses",
        json={
            "program_id": program.id,
            "code": course.code,
            "name": "Duplicate Code",
            "credit_hours": 3,
            "semester": 1,
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 409


async def test_create_course_same_code_different_semester_allowed(client, faculty, program, course):
    """Uniqueness is (programme, code, semester) -- not code alone."""
    resp = await client.post(
        "/api/v1/courses",
        json={
            "program_id": program.id,
            "code": course.code,
            "name": "Retake Offering",
            "credit_hours": 3,
            "semester": course.semester + 1,
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201


async def test_create_course_same_code_different_program_allowed(
    client, faculty, course, db_session
):
    from app.models.user import User as UserModel
    from app.schemas.department import DepartmentCreate
    from app.schemas.program import ProgramCreate
    from app.services import department_service, program_service

    department = await department_service.create_department(
        db_session, DepartmentCreate(name="Second Dept", code="SECOND-DEPT")
    )
    other_program = await program_service.create_program(
        db_session,
        ProgramCreate(dept_id=department.id, code="BSDS-TEST", name="BS Data Science", total_semesters=8),
        # create_program only branches on role == sub_admin (to enforce dept
        # scoping); an unpersisted faculty stand-in is enough here, same
        # pattern as conftest.py's `make_plo` fixture.
        current_user=UserModel(role=UserRole.faculty),
    )

    resp = await client.post(
        "/api/v1/courses",
        json={
            "program_id": other_program.id,
            "code": course.code,
            "name": "Same Code, Other Programme",
            "credit_hours": 3,
            "semester": course.semester,
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201


async def test_update_course_into_conflicting_combination_is_rejected(
    client, faculty, program, course
):
    """A PATCH that only changes `semester` must still be checked against the
    full (programme, code, semester) combination, not just the changed field."""
    other = await client.post(
        "/api/v1/courses",
        json={
            "program_id": program.id,
            "code": "CS-DUP",
            "name": "Second Course",
            "credit_hours": 3,
            "semester": course.semester + 1,
        },
        headers=auth_header(faculty),
    )
    assert other.status_code == 201
    other_id = other.json()["id"]

    resp = await client.patch(
        f"/api/v1/courses/{other_id}",
        json={"semester": course.semester, "code": course.code},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 409


async def test_faculty_cannot_access_another_faculty_course(client, make_user, course):
    other = await make_user(
        "faculty.other@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-OTHER"
    )
    resp = await client.get(f"/api/v1/courses/{course.id}", headers=auth_header(other))
    assert resp.status_code == 403


async def test_sub_admin_can_access_any_course_in_their_department(
    client, make_user, course, department
):
    sub_admin = await make_user(
        "subadmin.course@adaptobe.edu",
        role=UserRole.sub_admin,
        dept_id=department.id,
        employee_id="EMP-COURSE",
    )
    resp = await client.get(f"/api/v1/courses/{course.id}", headers=auth_header(sub_admin))
    assert resp.status_code == 200


async def test_sub_admin_cannot_access_course_in_other_department(
    client, make_user, course, db_session
):
    other_department = await department_service.create_department(
        db_session, DepartmentCreate(name="Other Department", code="OTHER-COURSE")
    )
    sub_admin = await make_user(
        "subadmin.othercourse@adaptobe.edu",
        role=UserRole.sub_admin,
        dept_id=other_department.id,
        employee_id="EMP-OTHERCOURSE",
    )
    resp = await client.get(f"/api/v1/courses/{course.id}", headers=auth_header(sub_admin))
    assert resp.status_code == 403


async def test_owner_can_update_course(client, faculty, course):
    resp = await client.patch(
        f"/api/v1/courses/{course.id}",
        json={"name": "Intro to Programming (Revised)"},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Intro to Programming (Revised)"


async def test_list_mine_filters_to_owned_courses(client, make_user, faculty, course, program):
    other = await make_user(
        "faculty.mine@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-MINE"
    )
    await client.post(
        "/api/v1/courses",
        json={
            "program_id": program.id,
            "code": "CS-777",
            "name": "Other Faculty Course",
            "credit_hours": 3,
            "semester": 2,
        },
        headers=auth_header(other),
    )

    resp = await client.get("/api/v1/courses?mine=true", headers=auth_header(faculty))
    assert resp.status_code == 200
    codes = [c["code"] for c in resp.json()]
    assert course.code in codes
    assert "CS-777" not in codes


async def test_get_course_not_found(client, faculty):
    resp = await client.get("/api/v1/courses/999999", headers=auth_header(faculty))
    assert resp.status_code == 404
