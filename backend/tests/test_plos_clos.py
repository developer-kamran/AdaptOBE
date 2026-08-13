from sqlalchemy import select

from app.ml import embeddings
from app.models.clo import CLO
from app.models.plo import PLO
from app.models.user import UserRole
from tests.conftest import auth_header


async def test_create_plo_requires_sub_admin(client, make_user, program):
    faculty = await make_user(
        "faculty.plo@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-PLO"
    )
    resp = await client.post(
        "/api/v1/admin/plos",
        json={
            "program_id": program.id,
            "code": "PLO-1",
            "title": "Engineering Knowledge",
            "description": "Apply knowledge of mathematics and engineering fundamentals.",
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 403


async def test_create_plo_generates_embedding(client, db_session, sub_admin, program):
    resp = await client.post(
        "/api/v1/admin/plos",
        json={
            "program_id": program.id,
            "code": "PLO-1",
            "title": "Engineering Knowledge",
            "description": "Apply knowledge of mathematics and engineering fundamentals.",
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 201
    plo_id = resp.json()["id"]

    stored = (await db_session.execute(select(PLO).where(PLO.id == plo_id))).scalar_one()
    assert stored.embedding is not None
    assert len(stored.embedding) == embeddings.EMBEDDING_DIM


async def test_plo_embedding_regenerated_on_description_change(client, db_session, sub_admin, make_plo):
    plo = await make_plo("PLO-9", "Original Title", "Original description about databases.")
    original = list(plo.embedding)

    resp = await client.patch(
        f"/api/v1/admin/plos/{plo.id}",
        json={"description": "Completely different text concerning ethics and society."},
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 200

    await db_session.refresh(plo)
    assert list(plo.embedding) != original


async def test_create_clo_generates_embedding(client, db_session, faculty, course):
    resp = await client.post(
        f"/api/v1/courses/{course.id}/clos",
        json={
            "code": "CLO-1",
            "title": "Write Programs",
            "description": "Write and debug simple programs using loops and functions.",
            "bloom_level": "Apply",
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201
    clo_id = resp.json()["id"]

    stored = (await db_session.execute(select(CLO).where(CLO.id == clo_id))).scalar_one()
    assert stored.embedding is not None
    assert len(stored.embedding) == embeddings.EMBEDDING_DIM


async def test_create_clo_rejects_non_owner_faculty(client, make_user, course):
    other = await make_user(
        "faculty.cloother@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-CLOOTHER"
    )
    resp = await client.post(
        f"/api/v1/courses/{course.id}/clos",
        json={
            "code": "CLO-X",
            "title": "Blocked",
            "description": "Should not be created by a non-owner.",
            "bloom_level": "Apply",
        },
        headers=auth_header(other),
    )
    assert resp.status_code == 403


async def test_create_clo_rejects_students(client, make_user, course):
    student = await make_user(
        "student.clo@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-CLO",
        seat_no="SEAT-CLO",
        father_name="Father Clo",
    )
    resp = await client.post(
        f"/api/v1/courses/{course.id}/clos",
        json={
            "code": "CLO-S",
            "title": "Blocked",
            "description": "Students may not do this.",
            "bloom_level": "Apply",
        },
        headers=auth_header(student),
    )
    assert resp.status_code == 403


async def test_create_clo_course_not_found(client, faculty):
    resp = await client.post(
        "/api/v1/courses/999999/clos",
        json={
            "code": "CLO-1",
            "title": "Ghost",
            "description": "No such course.",
            "bloom_level": "Apply",
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 404


async def test_create_clo_requires_bloom_level(client, faculty, course):
    resp = await client.post(
        f"/api/v1/courses/{course.id}/clos",
        json={"code": "CLO-NB", "title": "No Bloom Level", "description": "Missing bloom level."},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422


async def test_create_clo_rejects_invalid_bloom_level(client, faculty, course):
    resp = await client.post(
        f"/api/v1/courses/{course.id}/clos",
        json={
            "code": "CLO-BAD",
            "title": "Bad Bloom Level",
            "description": "Not one of the six standard levels.",
            "bloom_level": "Synthesize",
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422


async def test_update_clo(client, faculty, make_clo):
    clo = await make_clo("CLO-EDIT", "Original Title", "Original description.")
    resp = await client.patch(
        f"/api/v1/clos/{clo.id}",
        json={"title": "Updated Title", "bloom_level": "Evaluate"},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["bloom_level"] == "Evaluate"


async def test_delete_clo_untags_questions_and_recalculates(
    client, db_session, faculty, course, make_clo, make_assessment, make_question, make_student, enroll
):
    from sqlalchemy import select

    from app.models.attainment import AttainmentRecord

    clo = await make_clo("CLO-DEL", "To Delete", "Will be removed.")
    student = await make_student("clodelete")
    await enroll(student)
    assessment = await make_assessment(total_marks=10.0)
    question = await make_question(assessment.id, 1, 10.0, clo.id)

    resp = await client.delete(f"/api/v1/clos/{clo.id}", headers=auth_header(faculty))
    assert resp.status_code == 204

    await db_session.refresh(question)
    assert question.clo_id is None

    records = await db_session.execute(
        select(AttainmentRecord).where(AttainmentRecord.clo_id == clo.id)
    )
    assert list(records.scalars().all()) == []


async def test_delete_clo_rejects_non_owner(client, make_user, make_clo):
    other = await make_user(
        "faculty.clodeleteother@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-CLODEL"
    )
    clo = await make_clo("CLO-PROT", "Protected", "Owned by someone else.")
    resp = await client.delete(f"/api/v1/clos/{clo.id}", headers=auth_header(other))
    assert resp.status_code == 403


async def test_list_clos_for_course(client, faculty, course, make_clo):
    await make_clo("CLO-1", "First Outcome", "Understand basic programming constructs.")
    await make_clo("CLO-2", "Second Outcome", "Apply algorithms to solve problems.")

    resp = await client.get(f"/api/v1/courses/{course.id}/clos", headers=auth_header(faculty))
    assert resp.status_code == 200
    assert [c["code"] for c in resp.json()] == ["CLO-1", "CLO-2"]


async def test_list_plos_filtered_by_program(client, sub_admin, make_plo, program):
    await make_plo("PLO-1", "Knowledge", "Apply engineering knowledge.")

    resp = await client.get(
        f"/api/v1/admin/plos?program_id={program.id}", headers=auth_header(sub_admin)
    )
    assert resp.status_code == 200
    assert all(p["program_id"] == program.id for p in resp.json())
    assert len(resp.json()) >= 1


async def test_faculty_can_read_plos(client, faculty, make_plo):
    """Faculty don't manage PLOs, but need to read them to confirm CLO-PLO mappings."""
    plo = await make_plo("PLO-1", "Knowledge", "Apply engineering knowledge.")

    list_resp = await client.get("/api/v1/admin/plos", headers=auth_header(faculty))
    assert list_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/admin/plos/{plo.id}", headers=auth_header(faculty))
    assert get_resp.status_code == 200


async def test_students_cannot_read_plos(client, make_user):
    student = await make_user(
        "student.ploread@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-PLOREAD",
        seat_no="SEAT-PLOREAD",
        father_name="Father Ploread",
    )
    resp = await client.get("/api/v1/admin/plos", headers=auth_header(student))
    assert resp.status_code == 403


async def test_faculty_cannot_write_plos(client, faculty, program):
    resp = await client.post(
        "/api/v1/admin/plos",
        json={
            "program_id": program.id,
            "code": "PLO-X",
            "title": "Blocked",
            "description": "Faculty should not be able to create PLOs.",
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 403
