from app.models.user import UserRole
from tests.conftest import auth_header


async def test_list_users_requires_admin(client, make_user):
    student = await make_user("student.list@adaptobe.edu", role=UserRole.student)
    resp = await client.get("/api/v1/admin/users", headers=auth_header(student))
    assert resp.status_code == 403


async def test_list_users_unauthenticated(client):
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code == 401


async def test_list_users_as_admin(client, make_user):
    admin = await make_user("admin.list@adaptobe.edu", role=UserRole.admin)
    await make_user("listed@adaptobe.edu", role=UserRole.student)

    resp = await client.get("/api/v1/admin/users", headers=auth_header(admin))
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert "listed@adaptobe.edu" in emails


async def test_get_user_not_found(client, make_user):
    admin = await make_user("admin.get404@adaptobe.edu", role=UserRole.admin)
    resp = await client.get("/api/v1/admin/users/999999", headers=auth_header(admin))
    assert resp.status_code == 404


async def test_update_user_success(client, make_user):
    admin = await make_user("admin.update@adaptobe.edu", role=UserRole.admin)
    target = await make_user("target.update@adaptobe.edu", role=UserRole.student)

    resp = await client.patch(
        f"/api/v1/admin/users/{target.id}",
        json={"full_name": "Updated Name"},
        headers=auth_header(admin),
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"


async def test_update_user_duplicate_email_conflict(client, make_user):
    admin = await make_user("admin.updatedup@adaptobe.edu", role=UserRole.admin)
    user_a = await make_user("usera@adaptobe.edu", role=UserRole.student)
    user_b = await make_user("userb@adaptobe.edu", role=UserRole.student)

    resp = await client.patch(
        f"/api/v1/admin/users/{user_b.id}",
        json={"email": user_a.email},
        headers=auth_header(admin),
    )
    assert resp.status_code == 409


async def test_deactivate_user(client, make_user):
    admin = await make_user("admin.deactivate@adaptobe.edu", role=UserRole.admin)
    target = await make_user(
        "deactivate.me@adaptobe.edu", password="password123", role=UserRole.student
    )

    resp = await client.delete(
        f"/api/v1/admin/users/{target.id}", headers=auth_header(admin)
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "deactivate.me@adaptobe.edu", "password": "password123"},
    )
    assert login_resp.status_code == 401
