from app.models.user import UserRole
from tests.conftest import auth_header


async def test_create_course_requires_faculty_or_admin(client, make_user, program):
    student = await make_user("student.course@adaptobe.edu", role=UserRole.student)
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
    faculty = await make_user("faculty.create@adaptobe.edu", role=UserRole.faculty)
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


async def test_faculty_cannot_access_another_faculty_course(client, make_user, course):
    other = await make_user("faculty.other@adaptobe.edu", role=UserRole.faculty)
    resp = await client.get(f"/api/v1/courses/{course.id}", headers=auth_header(other))
    assert resp.status_code == 403


async def test_admin_can_access_any_course(client, make_user, course):
    admin = await make_user("admin.course@adaptobe.edu", role=UserRole.admin)
    resp = await client.get(f"/api/v1/courses/{course.id}", headers=auth_header(admin))
    assert resp.status_code == 200


async def test_owner_can_update_course(client, faculty, course):
    resp = await client.patch(
        f"/api/v1/courses/{course.id}",
        json={"name": "Intro to Programming (Revised)"},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Intro to Programming (Revised)"


async def test_list_mine_filters_to_owned_courses(client, make_user, faculty, course, program):
    other = await make_user("faculty.mine@adaptobe.edu", role=UserRole.faculty)
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
