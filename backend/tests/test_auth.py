from app.models.user import UserRole
from tests.conftest import auth_header


async def _sub_admin(make_user, suffix: str, department):
    return await make_user(
        f"subadmin.{suffix}@adaptobe.edu",
        role=UserRole.sub_admin,
        dept_id=department.id,
        employee_id=f"EMP-{suffix}",
    )


async def test_register_requires_authentication(client):
    payload = {
        "email": "noauth@adaptobe.edu",
        "password": "password123",
        "full_name": "No Auth",
        "role": "student",
        "enrollment_no": "ENR-NOAUTH",
        "seat_no": "SEAT-NOAUTH",
        "father_name": "Father Noauth",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 401


async def test_register_rejects_non_admin(client, make_user):
    student = await make_user(
        "student.reg@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-REG",
        seat_no="SEAT-REG",
        father_name="Father Reg",
    )
    payload = {
        "email": "blocked@adaptobe.edu",
        "password": "password123",
        "full_name": "Blocked",
        "role": "student",
        "enrollment_no": "ENR-BLOCKED",
        "seat_no": "SEAT-BLOCKED",
        "father_name": "Father Blocked",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(student)
    )
    assert resp.status_code == 403


async def test_register_success_as_sub_admin(client, make_user, department):
    sub_admin = await _sub_admin(make_user, "reg", department)
    payload = {
        "email": "newfaculty@adaptobe.edu",
        "password": "password123",
        "full_name": "New Faculty",
        "role": "faculty",
        "employee_id": "FAC-NEW",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(sub_admin)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "newfaculty@adaptobe.edu"
    assert body["role"] == "faculty"
    assert body["dept_id"] == department.id
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_success_as_super_admin(client, make_user, department):
    super_admin = await make_user("superadmin.reg@adaptobe.edu", role=UserRole.super_admin)
    payload = {
        "email": "newsubadmin@adaptobe.edu",
        "password": "password123",
        "full_name": "New Sub Admin",
        "role": "sub_admin",
        "dept_id": department.id,
        "employee_id": "EMP-NEWSUB",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(super_admin)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "sub_admin"
    assert body["dept_id"] == department.id


async def test_register_duplicate_email_conflict(client, make_user, department):
    sub_admin = await _sub_admin(make_user, "dup", department)
    existing = await make_user(
        "dup@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-DUP1",
        seat_no="SEAT-DUP1",
        father_name="Father Dup1",
    )
    payload = {
        "email": existing.email,
        "password": "password123",
        "full_name": "Duplicate",
        "role": "student",
        "enrollment_no": "ENR-DUP2",
        "seat_no": "SEAT-DUP2",
        "father_name": "Father Dup2",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(sub_admin)
    )
    assert resp.status_code == 409


async def test_register_duplicate_enrollment_no_conflict(client, make_user, department):
    sub_admin = await _sub_admin(make_user, "enroll", department)
    await make_user(
        "enroll1@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-001",
        seat_no="SEAT-E1",
        father_name="Father Enroll1",
    )
    payload = {
        "email": "enroll2@adaptobe.edu",
        "password": "password123",
        "full_name": "Enroll Two",
        "role": "student",
        "enrollment_no": "ENR-001",
        "seat_no": "SEAT-E2",
        "father_name": "Father Enroll2",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(sub_admin)
    )
    assert resp.status_code == 409


async def test_register_duplicate_seat_no_conflict(client, make_user, department):
    sub_admin = await _sub_admin(make_user, "seat", department)
    await make_user(
        "seat1@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-S1",
        seat_no="SEAT-001",
        father_name="Father Seat1",
    )
    payload = {
        "email": "seat2@adaptobe.edu",
        "password": "password123",
        "full_name": "Seat Two",
        "role": "student",
        "enrollment_no": "ENR-S2",
        "seat_no": "SEAT-001",
        "father_name": "Father Seat2",
    }
    resp = await client.post(
        "/api/v1/auth/register", json=payload, headers=auth_header(sub_admin)
    )
    assert resp.status_code == 409


async def test_login_success(client, make_user):
    await make_user(
        "login@adaptobe.edu",
        password="correct-password",
        role=UserRole.faculty,
        employee_id="FAC-LOGIN",
    )
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
    await make_user(
        "wrongpw@adaptobe.edu",
        password="correct-password",
        role=UserRole.faculty,
        employee_id="FAC-WRONGPW",
    )
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


async def test_login_inactive_user_rejected(client, make_user, db_session, department):
    from app.services.user_service import deactivate_user

    sub_admin = await _sub_admin(make_user, "inactive", department)
    user = await make_user(
        "inactive@adaptobe.edu",
        password="password123",
        role=UserRole.faculty,
        dept_id=department.id,
        employee_id="FAC-INACTIVE",
    )
    await deactivate_user(db_session, user.id, sub_admin)

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@adaptobe.edu", "password": "password123"},
    )
    assert resp.status_code == 401


async def test_refresh_returns_new_access_token(client, make_user):
    await make_user(
        "refresh@adaptobe.edu",
        password="password123",
        role=UserRole.faculty,
        employee_id="FAC-REFRESH",
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@adaptobe.edu", "password": "password123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_rejects_access_token(client, make_user):
    await make_user(
        "refreshbad@adaptobe.edu",
        password="password123",
        role=UserRole.faculty,
        employee_id="FAC-REFRESHBAD",
    )
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


async def test_me_returns_current_user(client, make_user):
    user = await make_user(
        "me@adaptobe.edu", full_name="Me User", role=UserRole.faculty, employee_id="FAC-ME"
    )
    resp = await client.get("/api/v1/auth/me", headers=auth_header(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@adaptobe.edu"
    assert body["role"] == "faculty"
    assert "password" not in body


async def test_me_requires_authentication(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
