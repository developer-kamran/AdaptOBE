from app.models.user import UserRole
from tests.conftest import auth_header


async def test_list_students_requires_faculty_or_admin(client, make_user):
    student = await make_user("student.list2@adaptobe.edu", role=UserRole.student)
    resp = await client.get("/api/v1/students", headers=auth_header(student))
    assert resp.status_code == 403


async def test_list_students_unauthenticated(client):
    resp = await client.get("/api/v1/students")
    assert resp.status_code == 401


async def test_faculty_can_list_active_students(client, make_user):
    faculty = await make_user("faculty.liststudents@adaptobe.edu", role=UserRole.faculty)
    active = await make_user("active.student@adaptobe.edu", role=UserRole.student)
    await make_user("other.faculty@adaptobe.edu", role=UserRole.faculty)

    resp = await client.get("/api/v1/students", headers=auth_header(faculty))
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert active.email in emails
    assert "other.faculty@adaptobe.edu" not in emails


async def test_inactive_students_excluded(client, make_user, db_session):
    from app.services.user_service import deactivate_user

    faculty = await make_user("faculty.liststudents2@adaptobe.edu", role=UserRole.faculty)
    inactive = await make_user("inactive.student2@adaptobe.edu", role=UserRole.student)
    await deactivate_user(db_session, inactive.id)

    resp = await client.get("/api/v1/students", headers=auth_header(faculty))
    assert resp.status_code == 200
    assert inactive.email not in [u["email"] for u in resp.json()]


async def test_admin_can_list_students(client, make_user):
    admin = await make_user("admin.liststudents@adaptobe.edu", role=UserRole.admin)
    resp = await client.get("/api/v1/students", headers=auth_header(admin))
    assert resp.status_code == 200
