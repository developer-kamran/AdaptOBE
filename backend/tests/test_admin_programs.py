from app.models.user import UserRole
from tests.conftest import auth_header


async def _create_department(client, super_admin, code: str) -> int:
    resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": f"Dept {code}", "code": code},
        headers=auth_header(super_admin),
    )
    return resp.json()["id"]


async def _create_department_and_sub_admin(client, make_user, code: str):
    super_admin = await make_user(f"superadmin.{code.lower()}@adaptobe.edu", role=UserRole.super_admin)
    dept_id = await _create_department(client, super_admin, code)
    sub_admin = await make_user(
        f"subadmin.{code.lower()}@adaptobe.edu",
        role=UserRole.sub_admin,
        dept_id=dept_id,
        employee_id=f"EMP-{code}",
    )
    return dept_id, sub_admin


async def test_create_program_requires_sub_admin(client, make_user):
    student = await make_user(
        "student.prog@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-PROG",
        seat_no="SEAT-PROG",
        father_name="Father Prog",
    )
    resp = await client.post(
        "/api/v1/admin/programs",
        json={"code": "BSCS-X", "name": "BS CS", "total_semesters": 8},
        headers=auth_header(student),
    )
    assert resp.status_code == 403


async def test_create_and_list_programs(client, make_user):
    _, sub_admin = await _create_department_and_sub_admin(client, make_user, "PROG1")

    resp = await client.post(
        "/api/v1/admin/programs",
        json={
            "code": "BSCS-P1",
            "name": "BS Computer Science",
            "total_semesters": 8,
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "BSCS-P1"
    program_id = resp.json()["id"]

    list_resp = await client.get("/api/v1/admin/programs", headers=auth_header(sub_admin))
    assert list_resp.status_code == 200
    assert any(p["id"] == program_id for p in list_resp.json())


async def test_create_program_duplicate_code_conflict(client, make_user):
    _, sub_admin = await _create_department_and_sub_admin(client, make_user, "PROGDUP")

    payload = {
        "code": "BSSE-DUP",
        "name": "BS Software Engineering",
        "total_semesters": 8,
    }
    first = await client.post(
        "/api/v1/admin/programs", json=payload, headers=auth_header(sub_admin)
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/admin/programs",
        json={**payload, "name": "Another Programme"},
        headers=auth_header(sub_admin),
    )
    assert second.status_code == 409


async def test_create_program_invalid_total_semesters(client, make_user):
    _, sub_admin = await _create_department_and_sub_admin(client, make_user, "PROG2")

    resp = await client.post(
        "/api/v1/admin/programs",
        json={
            "code": "BAD-SEM",
            "name": "Bad Program",
            "total_semesters": 0,
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 422


async def test_update_and_delete_program(client, make_user):
    _, sub_admin = await _create_department_and_sub_admin(client, make_user, "PROG3")

    create_resp = await client.post(
        "/api/v1/admin/programs",
        json={
            "code": "BSSE-P3",
            "name": "BS Software Engineering",
            "total_semesters": 8,
        },
        headers=auth_header(sub_admin),
    )
    program_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/admin/programs/{program_id}",
        json={"total_semesters": 10},
        headers=auth_header(sub_admin),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["total_semesters"] == 10

    delete_resp = await client.delete(
        f"/api/v1/admin/programs/{program_id}", headers=auth_header(sub_admin)
    )
    assert delete_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/admin/programs/{program_id}", headers=auth_header(sub_admin)
    )
    assert get_resp.status_code == 404


async def test_faculty_can_read_programs(client, make_user):
    """Faculty don't manage programmes, but need to read them to create a course."""
    _, sub_admin = await _create_department_and_sub_admin(client, make_user, "PROGREAD")
    faculty = await make_user(
        "faculty.progread@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-PROGREAD"
    )
    create_resp = await client.post(
        "/api/v1/admin/programs",
        json={"code": "BSXX-R", "name": "BS Testing", "total_semesters": 8},
        headers=auth_header(sub_admin),
    )
    program_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/admin/programs", headers=auth_header(faculty))
    assert list_resp.status_code == 200

    get_resp = await client.get(
        f"/api/v1/admin/programs/{program_id}", headers=auth_header(faculty)
    )
    assert get_resp.status_code == 200


async def test_students_cannot_read_programs(client, make_user):
    student = await make_user(
        "student.progread@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-PROGREAD",
        seat_no="SEAT-PROGREAD",
        father_name="Father Progread",
    )
    resp = await client.get("/api/v1/admin/programs", headers=auth_header(student))
    assert resp.status_code == 403


async def test_faculty_cannot_write_programs(client, make_user):
    _, sub_admin = await _create_department_and_sub_admin(client, make_user, "PROGWRITE")
    faculty = await make_user(
        "faculty.progwrite@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-PROGWRITE"
    )

    resp = await client.post(
        "/api/v1/admin/programs",
        json={"code": "BLOCKED", "name": "Blocked", "total_semesters": 8},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 403


async def test_super_admin_cannot_write_programs(client, make_user):
    """super_admin manages departments/sub-admins only, not programmes."""
    dept_id, _ = await _create_department_and_sub_admin(client, make_user, "PROGSUPER")
    super_admin = await make_user("superadmin.progsuper2@adaptobe.edu", role=UserRole.super_admin)

    resp = await client.post(
        "/api/v1/admin/programs",
        json={"code": "SUPERBLOCK", "name": "Blocked", "total_semesters": 8},
        headers=auth_header(super_admin),
    )
    assert resp.status_code == 403
