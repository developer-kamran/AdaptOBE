from app.models.user import UserRole
from tests.conftest import auth_header


async def test_register_requires_authentication(client):
    payload = {
        "email": "noauth@adaptobe.edu",
        "password": "password123",
        "full_name": "No Auth",
        "role": "student",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 401


async def test_register_rejects_non_admin(client, make_user):
    student = await make_user("student.reg@adaptobe.edu", role=UserRole.student)
    payload = {
        "email": "blocked@adaptobe.edu",
        "password": "password123",
        "full_name": "Blocked",
        "role": "student",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(student)
    )
    assert resp.status_code == 403


async def test_register_success_as_admin(client, make_user):
    admin = await make_user("admin.reg@adaptobe.edu", role=UserRole.admin)
    payload = {
        "email": "newfaculty@adaptobe.edu",
        "password": "password123",
        "full_name": "New Faculty",
        "role": "faculty",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(admin)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "newfaculty@adaptobe.edu"
    assert body["role"] == "faculty"
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_duplicate_email_conflict(client, make_user):
    admin = await make_user("admin.dup@adaptobe.edu", role=UserRole.admin)
    existing = await make_user("dup@adaptobe.edu", role=UserRole.student)
    payload = {
        "email": existing.email,
        "password": "password123",
        "full_name": "Duplicate",
        "role": "student",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(admin)
    )
    assert resp.status_code == 409


async def test_register_duplicate_enrollment_no_conflict(client, make_user):
    admin = await make_user("admin.enroll@adaptobe.edu", role=UserRole.admin)
    await make_user(
        "enroll1@adaptobe.edu", role=UserRole.student, enrollment_no="ENR-001"
    )
    payload = {
        "email": "enroll2@adaptobe.edu",
        "password": "password123",
        "full_name": "Enroll Two",
        "role": "student",
        "enrollment_no": "ENR-001",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(admin)
    )
    assert resp.status_code == 409


async def test_register_duplicate_seat_no_conflict(client, make_user):
    admin = await make_user("admin.seat@adaptobe.edu", role=UserRole.admin)
    await make_user("seat1@adaptobe.edu", role=UserRole.student, seat_no="SEAT-001")
    payload = {
        "email": "seat2@adaptobe.edu",
        "password": "password123",
        "full_name": "Seat Two",
        "role": "student",
        "seat_no": "SEAT-001",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(admin)
    )
    assert resp.status_code == 409


async def test_login_success(client, make_user):
    await make_user("login@adaptobe.edu", password="correct-password", role=UserRole.student)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@adaptobe.edu", "password": "correct-password"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client, make_user):
    await make_user("wrongpw@adaptobe.edu", password="correct-password")
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@adaptobe.edu", "password": "wrong-password"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent_email(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@adaptobe.edu", "password": "whatever123"},
    )
    assert resp.status_code == 401


async def test_login_inactive_user_rejected(client, make_user, db_session):
    from app.services.user_service import deactivate_user

    user = await make_user("inactive@adaptobe.edu", password="password123")
    await deactivate_user(db_session, user.id)

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@adaptobe.edu", "password": "password123"},
    )
    assert resp.status_code == 401


async def test_refresh_returns_new_access_token(client, make_user):
    await make_user("refresh@adaptobe.edu", password="password123")
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@adaptobe.edu", "password": "password123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_rejects_access_token(client, make_user):
    await make_user("refreshbad@adaptobe.edu", password="password123")
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "refreshbad@adaptobe.edu", "password": "password123"},
    )
    access_token = login_resp.json()["access_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


async def test_refresh_rejects_garbage_token(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert resp.status_code == 401
