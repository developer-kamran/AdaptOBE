from app.models.user import UserRole
from tests.conftest import auth_header


async def test_create_department_requires_super_admin(client, make_user):
    faculty = await make_user(
        "faculty.dept@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-DEPT"
    )
    resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Computer Science", "code": "CS"},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 403


async def test_create_and_get_department(client, make_user):
    admin = await make_user("superadmin.dept@adaptobe.edu", role=UserRole.super_admin)
    resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Electrical Engineering", "code": "EE"},
        headers=auth_header(admin),
    )
    assert resp.status_code == 201
    dept_id = resp.json()["id"]

    get_resp = await client.get(
        f"/api/v1/admin/departments/{dept_id}", headers=auth_header(admin)
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["code"] == "EE"


async def test_create_department_duplicate_code_conflict(client, make_user):
    admin = await make_user("superadmin.deptdup@adaptobe.edu", role=UserRole.super_admin)
    await client.post(
        "/api/v1/admin/departments",
        json={"name": "Mechanical Engineering", "code": "ME"},
        headers=auth_header(admin),
    )
    resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Mechanical Engineering Duplicate", "code": "ME"},
        headers=auth_header(admin),
    )
    assert resp.status_code == 409


async def test_get_department_not_found(client, make_user):
    admin = await make_user("superadmin.dept404@adaptobe.edu", role=UserRole.super_admin)
    resp = await client.get("/api/v1/admin/departments/999999", headers=auth_header(admin))
    assert resp.status_code == 404


async def test_update_department(client, make_user):
    admin = await make_user("superadmin.deptupdate@adaptobe.edu", role=UserRole.super_admin)
    create_resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Civil Engineering", "code": "CE"},
        headers=auth_header(admin),
    )
    dept_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/admin/departments/{dept_id}",
        json={"name": "Civil & Environmental Engineering"},
        headers=auth_header(admin),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Civil & Environmental Engineering"


async def test_delete_department(client, make_user):
    admin = await make_user("superadmin.deptdelete@adaptobe.edu", role=UserRole.super_admin)
    create_resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": "Chemical Engineering", "code": "CHE"},
        headers=auth_header(admin),
    )
    dept_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/admin/departments/{dept_id}", headers=auth_header(admin)
    )
    assert resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/admin/departments/{dept_id}", headers=auth_header(admin)
    )
    assert get_resp.status_code == 404
