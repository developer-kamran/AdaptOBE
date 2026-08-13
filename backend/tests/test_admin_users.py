from app.models.user import UserRole
from tests.conftest import auth_header


async def _sub_admin_and_dept(make_user, suffix: str, department):
    sub_admin = await make_user(
        f"subadmin.{suffix}@adaptobe.edu",
        role=UserRole.sub_admin,
        dept_id=department.id,
        employee_id=f"EMP-{suffix}",
    )
    return sub_admin


async def test_list_users_requires_admin(client, make_user):
    student = await make_user(
        "student.list@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-LIST",
        seat_no="SEAT-LIST",
        father_name="Father List",
    )
    resp = await client.get("/api/v1/admin/users", headers=auth_header(student))
    assert resp.status_code == 403


async def test_list_users_unauthenticated(client):
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 401


async def test_super_admin_lists_only_sub_admins(client, make_user, department):
    super_admin = await make_user("superadmin.list@adaptobe.edu", role=UserRole.super_admin)
    sub_admin = await _sub_admin_and_dept(make_user, "list", department)
    await make_user(
        "student.listnotshown@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-LISTNOTSHOWN",
        seat_no="SEAT-LISTNOTSHOWN",
        father_name="Father Listnotshown",
    )

    resp = await client.get("/api/v1/admin/users", headers=auth_header(super_admin))
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert sub_admin.email in emails
    assert "student.listnotshown@adaptobe.edu" not in emails


async def test_sub_admin_lists_only_own_department_faculty_and_students(
    client, make_user, department
):
    sub_admin = await _sub_admin_and_dept(make_user, "listdept", department)
    student_in_dept = await make_user(
        "student.indept@adaptobe.edu",
        role=UserRole.student,
        dept_id=department.id,
        enrollment_no="ENR-IN",
        seat_no="SEAT-IN",
        father_name="Father In",
    )
    await make_user(
        "student.outofdept@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-OUT",
        seat_no="SEAT-OUT",
        father_name="Father Out",
    )

    resp = await client.get("/api/v1/admin/users", headers=auth_header(sub_admin))
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert student_in_dept.email in emails
    assert "student.outofdept@adaptobe.edu" not in emails


async def test_get_user_not_found(client, make_user, department):
    sub_admin = await _sub_admin_and_dept(make_user, "get404", department)
    resp = await client.get("/api/v1/admin/users/999999", headers=auth_header(sub_admin))
    assert resp.status_code == 404


async def test_update_user_success(client, make_user, department):
    sub_admin = await _sub_admin_and_dept(make_user, "update", department)
    target = await make_user(
        "target.update@adaptobe.edu",
        role=UserRole.student,
        dept_id=department.id,
        enrollment_no="ENR-UPD",
        seat_no="SEAT-UPD",
        father_name="Father Upd",
    )

    resp = await client.patch(
        f"/api/v1/admin/users/{target.id}",
        json={"full_name": "Updated Name"},
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"


async def test_update_user_duplicate_email_conflict(client, make_user, department):
    sub_admin = await _sub_admin_and_dept(make_user, "updatedup", department)
    user_a = await make_user(
        "usera@adaptobe.edu",
        role=UserRole.student,
        dept_id=department.id,
        enrollment_no="ENR-A",
        seat_no="SEAT-A",
        father_name="Father A",
    )
    user_b = await make_user(
        "userb@adaptobe.edu",
        role=UserRole.student,
        dept_id=department.id,
        enrollment_no="ENR-B",
        seat_no="SEAT-B",
        father_name="Father B",
    )

    resp = await client.patch(
        f"/api/v1/admin/users/{user_b.id}",
        json={"email": user_a.email},
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 409


async def test_deactivate_user(client, make_user, department):
    sub_admin = await _sub_admin_and_dept(make_user, "deactivate", department)
    target = await make_user(
        "deactivate.me@adaptobe.edu",
        password="password123",
        role=UserRole.student,
        dept_id=department.id,
        enrollment_no="ENR-DEACT",
        seat_no="SEAT-DEACT",
        father_name="Father Deact",
    )

    resp = await client.delete(
        f"/api/v1/admin/users/{target.id}", headers=auth_header(sub_admin)
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "deactivate.me@adaptobe.edu", "password": "password123"},
    )
    assert login_resp.status_code == 401


async def test_sub_admin_cannot_manage_user_in_other_department(client, make_user, department):
    sub_admin = await _sub_admin_and_dept(make_user, "crossdept", department)
    other_student = await make_user(
        "student.otherdept@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-OTHER",
        seat_no="SEAT-OTHER",
        father_name="Father Other",
    )

    resp = await client.get(
        f"/api/v1/admin/users/{other_student.id}", headers=auth_header(sub_admin)
    )
    assert resp.status_code == 403


async def test_super_admin_cannot_manage_faculty_or_student(client, make_user):
    super_admin = await make_user("superadmin.nofaculty@adaptobe.edu", role=UserRole.super_admin)
    student = await make_user(
        "student.nosuperadmin@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-NS",
        seat_no="SEAT-NS",
        father_name="Father Ns",
    )

    resp = await client.get(f"/api/v1/admin/users/{student.id}", headers=auth_header(super_admin))
    assert resp.status_code == 403
