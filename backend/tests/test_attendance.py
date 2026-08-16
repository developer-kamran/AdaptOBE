"""Attendance entry: service behavior, validation, and RBAC."""

from app.services import attendance_service
from tests.conftest import auth_header


async def test_set_and_list_attendance(
    db_session, course, make_student, enroll, client, faculty
):
    a = await make_student("att-a")
    b = await make_student("att-b")
    await enroll(a, b)

    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance",
        json={"entries": [
            {"student_id": a.id, "attendance_percentage": 80.0},
            {"student_id": b.id, "attendance_percentage": 55.0},
        ]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    assert resp.json()["saved"] == 2

    listing = await client.get(
        f"/api/v1/courses/{course.id}/attendance", headers=auth_header(faculty)
    )
    assert listing.status_code == 200
    by_student = {row["student_id"]: row["attendance_percentage"] for row in listing.json()}
    assert by_student == {a.id: 80.0, b.id: 55.0}


async def test_set_attendance_upserts(
    db_session, course, make_student, enroll, client, faculty
):
    student = await make_student("att-upsert")
    await enroll(student)

    await client.post(
        f"/api/v1/courses/{course.id}/attendance",
        json={"entries": [{"student_id": student.id, "attendance_percentage": 40.0}]},
        headers=auth_header(faculty),
    )
    await client.post(
        f"/api/v1/courses/{course.id}/attendance",
        json={"entries": [{"student_id": student.id, "attendance_percentage": 90.0}]},
        headers=auth_header(faculty),
    )

    mapping = await attendance_service.attendance_map(db_session, course.id)
    assert mapping[student.id] == 90.0  # updated, not duplicated


async def test_attendance_rejects_non_enrolled_student(
    db_session, course, make_student, client, faculty
):
    outsider = await make_student("att-outsider")  # never enrolled
    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance",
        json={"entries": [{"student_id": outsider.id, "attendance_percentage": 50.0}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422
    assert "not enrolled" in resp.json()["detail"].lower()


async def test_attendance_percentage_out_of_range_rejected(
    db_session, course, make_student, enroll, client, faculty
):
    student = await make_student("att-range")
    await enroll(student)
    resp = await client.post(
        f"/api/v1/courses/{course.id}/attendance",
        json={"entries": [{"student_id": student.id, "attendance_percentage": 150.0}]},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422  # schema Field(le=100)


async def test_attendance_is_faculty_only(
    db_session, course, make_student, client, sub_admin, super_admin
):
    student = await make_student("att-rbac")
    for actor in (sub_admin, super_admin, student):
        resp = await client.post(
            f"/api/v1/courses/{course.id}/attendance",
            json={"entries": [{"student_id": student.id, "attendance_percentage": 50.0}]},
            headers=auth_header(actor),
        )
        assert resp.status_code == 403
        listing = await client.get(
            f"/api/v1/courses/{course.id}/attendance", headers=auth_header(actor)
        )
        assert listing.status_code == 403
