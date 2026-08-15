from sqlalchemy import select

from app.models.mapping import CloPloMapping
from app.models.user import UserRole
from tests.conftest import auth_header


async def test_suggest_returns_top_3_ranked_by_similarity(client, faculty, make_plo, make_clo):
    await make_plo("PLO-1", "Database Design", "Design relational database schemas and queries.")
    await make_plo("PLO-2", "Professional Ethics", "Apply ethical reasoning in professional practice.")
    await make_plo("PLO-3", "Teamwork", "Function effectively as a member of a diverse team.")
    await make_plo("PLO-4", "Communication", "Communicate effectively through written reports.")

    clo = await make_clo(
        "CLO-1", "Database Schemas", "Design relational database schemas and queries."
    )

    resp = await client.post(
        "/api/v1/mappings/suggest", json={"clo_id": clo.id}, headers=auth_header(faculty)
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["clo_id"] == clo.id
    assert len(body["suggestions"]) == 3

    scores = [s["similarity_score"] for s in body["suggestions"]]
    assert scores == sorted(scores, reverse=True)

    # The CLO text is identical to PLO-1's, so it must rank first.
    assert body["suggestions"][0]["code"] == "PLO-1"


async def test_suggest_respects_limit(client, faculty, make_plo, make_clo):
    for index in range(5):
        await make_plo(f"PLO-{index}", f"Outcome {index}", f"Description number {index}.")
    clo = await make_clo("CLO-1", "Some Outcome", "Description number 2.")

    resp = await client.post(
        "/api/v1/mappings/suggest",
        json={"clo_id": clo.id, "limit": 2},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    assert len(resp.json()["suggestions"]) == 2


async def test_suggest_only_returns_plos_from_same_program(
    client, db_session, faculty, make_plo, make_clo
):
    from app.schemas.department import DepartmentCreate
    from app.schemas.program import ProgramCreate
    from app.services import department_service, program_service

    other_dept = await department_service.create_department(
        db_session, DepartmentCreate(name="Electrical", code="EE-TEST")
    )
    other_program = await program_service.create_program(
        db_session,
        ProgramCreate(
            dept_id=other_dept.id, code="BSEE-TEST", name="BS Electrical", total_semesters=8
        ),
        current_user=faculty,
    )

    await make_plo("PLO-SAME", "Programming", "Write and debug computer programs.")
    await make_plo(
        "PLO-OTHER",
        "Programming",
        "Write and debug computer programs.",
        program_id=other_program.id,
    )

    clo = await make_clo("CLO-1", "Programming", "Write and debug computer programs.")

    resp = await client.post(
        "/api/v1/mappings/suggest", json={"clo_id": clo.id}, headers=auth_header(faculty)
    )
    assert resp.status_code == 200
    codes = [s["code"] for s in resp.json()["suggestions"]]
    assert "PLO-SAME" in codes
    assert "PLO-OTHER" not in codes


async def test_suggest_with_no_plos_returns_empty(client, faculty, make_clo):
    clo = await make_clo("CLO-1", "Lonely Outcome", "There are no PLOs to match against.")
    resp = await client.post(
        "/api/v1/mappings/suggest", json={"clo_id": clo.id}, headers=auth_header(faculty)
    )
    assert resp.status_code == 200
    assert resp.json()["suggestions"] == []


async def test_suggest_rejects_non_owner(client, make_user, make_clo):
    other = await make_user(
        "faculty.suggest@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-SUGGEST"
    )
    clo = await make_clo("CLO-1", "Outcome", "Some description text.")
    resp = await client.post(
        "/api/v1/mappings/suggest", json={"clo_id": clo.id}, headers=auth_header(other)
    )
    assert resp.status_code == 403


async def test_suggest_clo_not_found(client, faculty):
    resp = await client.post(
        "/api/v1/mappings/suggest", json={"clo_id": 999999}, headers=auth_header(faculty)
    )
    assert resp.status_code == 404


async def test_confirm_creates_mapping(client, faculty, make_plo, make_clo):
    plo = await make_plo("PLO-1", "Design", "Design software systems.")
    clo = await make_clo("CLO-1", "Design", "Design software systems.")

    resp = await client.post(
        "/api/v1/mappings/confirm",
        json={
            "clo_id": clo.id,
            "plo_id": plo.id,
            "strength": 3,
            "is_ai_generated": True,
            "similarity_score": 0.91,
        },
        headers=auth_header(faculty),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["strength"] == 3
    assert body["is_ai_generated"] is True
    assert body["similarity_score"] == 0.91


async def test_confirm_twice_updates_instead_of_duplicating(
    client, db_session, faculty, make_plo, make_clo
):
    plo = await make_plo("PLO-1", "Design", "Design software systems.")
    clo = await make_clo("CLO-1", "Design", "Design software systems.")
    payload = {"clo_id": clo.id, "plo_id": plo.id, "strength": 1}

    first = await client.post(
        "/api/v1/mappings/confirm", json=payload, headers=auth_header(faculty)
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/mappings/confirm",
        json={**payload, "strength": 3},
        headers=auth_header(faculty),
    )
    assert second.status_code == 201
    assert second.json()["strength"] == 3
    assert second.json()["id"] == first.json()["id"]

    rows = await db_session.execute(
        select(CloPloMapping).where(
            CloPloMapping.clo_id == clo.id, CloPloMapping.plo_id == plo.id
        )
    )
    assert len(list(rows.scalars().all())) == 1


async def test_confirm_rejects_strength_out_of_range(client, faculty, make_plo, make_clo):
    plo = await make_plo("PLO-1", "Design", "Design software systems.")
    clo = await make_clo("CLO-1", "Design", "Design software systems.")

    for bad_strength in (0, 4, -1):
        resp = await client.post(
            "/api/v1/mappings/confirm",
            json={"clo_id": clo.id, "plo_id": plo.id, "strength": bad_strength},
            headers=auth_header(faculty),
        )
        assert resp.status_code == 422


async def test_confirm_rejects_cross_program_mapping(
    client, db_session, faculty, make_plo, make_clo
):
    from app.schemas.department import DepartmentCreate
    from app.schemas.program import ProgramCreate
    from app.services import department_service, program_service

    other_dept = await department_service.create_department(
        db_session, DepartmentCreate(name="Mechanical", code="ME-TEST")
    )
    other_program = await program_service.create_program(
        db_session,
        ProgramCreate(
            dept_id=other_dept.id, code="BSME-TEST", name="BS Mechanical", total_semesters=8
        ),
        current_user=faculty,
    )
    foreign_plo = await make_plo(
        "PLO-FOREIGN", "Thermo", "Apply thermodynamics.", program_id=other_program.id
    )
    clo = await make_clo("CLO-1", "Design", "Design software systems.")

    resp = await client.post(
        "/api/v1/mappings/confirm",
        json={"clo_id": clo.id, "plo_id": foreign_plo.id, "strength": 2},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422


async def test_confirm_rejects_non_owner(client, make_user, make_plo, make_clo):
    other = await make_user(
        "faculty.confirm@adaptobe.edu", role=UserRole.faculty, employee_id="FAC-CONFIRM"
    )
    plo = await make_plo("PLO-1", "Design", "Design software systems.")
    clo = await make_clo("CLO-1", "Design", "Design software systems.")

    resp = await client.post(
        "/api/v1/mappings/confirm",
        json={"clo_id": clo.id, "plo_id": plo.id, "strength": 2},
        headers=auth_header(other),
    )
    assert resp.status_code == 403


async def test_list_and_delete_mappings_for_clo(client, faculty, make_plo, make_clo):
    plo = await make_plo("PLO-1", "Design", "Design software systems.")
    clo = await make_clo("CLO-1", "Design", "Design software systems.")

    created = await client.post(
        "/api/v1/mappings/confirm",
        json={"clo_id": clo.id, "plo_id": plo.id, "strength": 2},
        headers=auth_header(faculty),
    )
    mapping_id = created.json()["id"]

    listed = await client.get(
        f"/api/v1/mappings/clo/{clo.id}", headers=auth_header(faculty)
    )
    assert listed.status_code == 200
    assert [m["id"] for m in listed.json()] == [mapping_id]

    deleted = await client.delete(
        f"/api/v1/mappings/{mapping_id}", headers=auth_header(faculty)
    )
    assert deleted.status_code == 204

    listed_again = await client.get(
        f"/api/v1/mappings/clo/{clo.id}", headers=auth_header(faculty)
    )
    assert listed_again.json() == []


async def test_suggest_rejects_students(client, make_user, make_clo):
    student = await make_user(
        "student.suggest@adaptobe.edu",
        role=UserRole.student,
        enrollment_no="ENR-SUGGEST",
        seat_no="SEAT-SUGGEST",
        father_name="Father Suggest",
    )
    clo = await make_clo("CLO-1", "Outcome", "Some description.")
    resp = await client.post(
        "/api/v1/mappings/suggest", json={"clo_id": clo.id}, headers=auth_header(student)
    )
    assert resp.status_code == 403
