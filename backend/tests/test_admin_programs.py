from app.models.user import UserRole
from tests.conftest import auth_header


async def _create_department(client, admin, code: str) -> int:
    resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": f"Dept {code}", "code": code},
        headers=auth_header(admin),
    )
    return resp.json()["id"]


async def test_create_program_requires_admin(client, make_user):
    student = await make_user("student.prog@adaptobe.edu", role=UserRole.student)
    resp = await client.post(
        "/api/v1/admin/programs",
        json={"dept_id": 1, "code": "BSCS-X", "name": "BS CS", "total_semesters": 8},
        headers=auth_header(student),
    )
    assert resp.status_code == 403


async def test_create_and_list_programs(client, make_user):
    admin = await make_user("admin.prog@adaptobe.edu", role=UserRole.admin)
    dept_id = await _create_department(client, admin, "PROG1")

    resp = await client.post(
        "/api/v1/admin/programs",
        json={
            "dept_id": dept_id,
            "code": "BSCS-P1",
            "name": "BS Computer Science",
            "total_semesters": 8,
        },
        headers=auth_header(admin),
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "BSCS-P1"
    program_id = resp.json()["id"]

    list_resp = await client.get("/api/v1/admin/programs", headers=auth_header(admin))
    assert list_resp.status_code == 200
    assert any(p["id"] == program_id for p in list_resp.json())


async def test_create_program_invalid_department_conflict(client, make_user):
    admin = await make_user("admin.proginvalid@adaptobe.edu", role=UserRole.admin)
    resp = await client.post(
        "/api/v1/admin/programs",
        json={
            "dept_id": 999999,
            "code": "GHOST",
            "name": "Ghost Program",
            "total_semesters": 8,
        },
        headers=auth_header(admin),
    )
    assert resp.status_code == 409


async def test_create_program_duplicate_code_conflict(client, make_user):
    admin = await make_user("admin.progdup@adaptobe.edu", role=UserRole.admin)
    dept_id = await _create_department(client, admin, "PROGDUP")

    payload = {
        "dept_id": dept_id,
        "code": "BSSE-DUP",
        "name": "BS Software Engineering",
        "total_semesters": 8,
    }
    first = await client.post(
        "/api/v1/admin/programs", json=payload, headers=auth_header(admin)
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/admin/programs",
        json={**payload, "name": "Another Programme"},
        headers=auth_header(admin),
    )
    assert second.status_code == 409


async def test_create_program_invalid_total_semesters(client, make_user):
    admin = await make_user("admin.progsem@adaptobe.edu", role=UserRole.admin)
    dept_id = await _create_department(client, admin, "PROG2")

    resp = await client.post(
        "/api/v1/admin/programs",
        json={
            "dept_id": dept_id,
            "code": "BAD-SEM",
            "name": "Bad Program",
            "total_semesters": 0,
        },
        headers=auth_header(admin),
    )
    assert resp.status_code == 422


async def test_update_and_delete_program(client, make_user):
    admin = await make_user("admin.progupdate@adaptobe.edu", role=UserRole.admin)
    dept_id = await _create_department(client, admin, "PROG3")

    create_resp = await client.post(
        "/api/v1/admin/programs",
        json={
            "dept_id": dept_id,
            "code": "BSSE-P3",
            "name": "BS Software Engineering",
            "total_semesters": 8,
        },
        headers=auth_header(admin),
    )
    program_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/admin/programs/{program_id}",
        json={"total_semesters": 10},
        headers=auth_header(admin),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["total_semesters"] == 10

    delete_resp = await client.delete(
        f"/api/v1/admin/programs/{program_id}", headers=auth_header(admin)
    )
    assert delete_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/admin/programs/{program_id}", headers=auth_header(admin)
    )
    assert get_resp.status_code == 404
