from app.models.user import UserRole
from tests.conftest import auth_header


async def test_list_students_requires_faculty_or_sub_admin(client, make_user):
    student = await make_user(
        "student.list2@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-LIST2",
        seat_no="SEAT-LIST2",
        father_name="Father List2",
    )
    resp = await client.get("/api/v1/students", headers=auth_header(student))
    assert resp.status_code == 403


async def test_list_students_unauthenticated(client):
    resp = await client.get("/api/v1/students")
    assert resp.status_code == 401


async def test_faculty_can_list_active_students(client, make_user):
    faculty = await make_user(
        "faculty.liststudents@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-LISTSTUDENTS"
    )
    active = await make_user(
        "active.student@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-ACTIVE",
        seat_no="SEAT-ACTIVE",
        father_name="Father Active",
    )
    await make_user(
        "other.faculty@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-OTHERLIST"
    )

    resp = await client.get("/api/v1/students", headers=auth_header(faculty))
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert active.email in emails
    assert "other.faculty@adaptobe.edu" not in emails


async def test_inactive_students_excluded(client, make_user, db_session, sub_admin, department):
    from app.services.user_service import deactivate_user

    faculty = await make_user(
        "faculty.liststudents2@adaptobe.edu",
        role=UserRole.faculty,
        employee_id="FAC-LISTSTUDENTS2",
    )
    inactive = await make_user(
        "inactive.student2@adaptobe.edu",
        role=UserRole.student,
        dept_id=department.id,
        enrollment_no="ENR-INACTIVE2",
        seat_no="SEAT-INACTIVE2",
        father_name="Father Inactive2",
    )
    await deactivate_user(db_session, inactive.id, sub_admin)

    resp = await client.get("/api/v1/students", headers=auth_header(faculty))
    assert resp.status_code == 200
    assert inactive.email not in [u["email"] for u in resp.json()]


async def test_sub_admin_can_list_students(client, sub_admin):
    resp = await client.get("/api/v1/students", headers=auth_header(sub_admin))
    assert resp.status_code == 200


async def test_faculty_only_sees_own_department_students(client, make_user, department):
    """Faculty have a dept_id too (same as sub-admins) -- a faculty member
    should not be offered another department's students to enroll, e.g. for
    backlog-student search."""
    faculty = await make_user(
        "faculty.deptscoped@adaptobe.edu",
        role=UserRole.faculty,
        dept_id=department.id,
        employee_id="FAC-DEPTSCOPED",
    )
    in_dept = await make_user(
        "student.facindept@adaptobe.edu",
        role=UserRole.student,
        dept_id=department.id,
        enrollment_no="ENR-FACINDEPT",
        seat_no="SEAT-FACINDEPT",
        father_name="Father Facindept",
    )
    await make_user(
        "student.facoutdept@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-FACOUTDEPT",
        seat_no="SEAT-FACOUTDEPT",
        father_name="Father Facoutdept",
    )

    resp = await client.get("/api/v1/students", headers=auth_header(faculty))
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert in_dept.email in emails
    assert "student.facoutdept@adaptobe.edu" not in emails


async def test_sub_admin_only_sees_own_department_students(client, make_user, sub_admin, department):
    in_dept = await make_user(
        "student.indeptlist@adaptobe.edu",
        role=UserRole.student,
        dept_id=department.id,
        enrollment_no="ENR-INDEPT",
        seat_no="SEAT-INDEPT",
        father_name="Father Indept",
    )
    await make_user(
        "student.outdeptlist@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-OUTDEPT",
        seat_no="SEAT-OUTDEPT",
        father_name="Father Outdept",
    )

    resp = await client.get("/api/v1/students", headers=auth_header(sub_admin))
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert in_dept.email in emails
    assert "student.outdeptlist@adaptobe.edu" not in emails
