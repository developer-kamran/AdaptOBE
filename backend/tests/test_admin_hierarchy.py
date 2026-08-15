"""Cross-cutting tests for the Super Admin / Sub-Admin hierarchy that don't
belong to any single resource's existing test file: cross-department
isolation, tier boundaries (super_admin vs sub_admin), and the new
student/PLO field validation rules.
"""
from app.models.user import UserRole
from app.schemas.department import DepartmentCreate
from app.schemas.program import ProgramCreate
from app.services import department_service, program_service
from tests.conftest import auth_header


async def _other_department_with_sub_admin_and_program(db_session, make_user, suffix: str):
    other_dept = await department_service.create_department(
        db_session, DepartmentCreate(name=f"Other Dept {suffix}", code=f"OTHER-{suffix}")
    )
    other_sub_admin = await make_user(
        f"subadmin.other{suffix}@adaptobe.edu",
        role=UserRole.sub_admin,
        dept_id=other_dept.id,
        employee_id=f"EMP-OTHER-{suffix}",
    )
    other_program = await program_service.create_program(
        db_session,
        ProgramCreate(code=f"PROG-OTHER-{suffix}", name="Other Programme", total_semesters=8),
        current_user=other_sub_admin,
    )
    return other_dept, other_sub_admin, other_program


# --- Cross-department isolation ---------------------------------------------


async def test_sub_admin_cannot_read_program_in_other_department(
    client, db_session, make_user, sub_admin
):
    _, _, other_program = await _other_department_with_sub_admin_and_program(
        db_session, make_user, "PROGREAD"
    )
    resp = await client.get(
        f"/api/v1/admin/programs/{other_program.id}", headers=auth_header(sub_admin)
    )
    assert resp.status_code == 403


async def test_sub_admin_cannot_update_program_in_other_department(
    client, db_session, make_user, sub_admin
):
    _, _, other_program = await _other_department_with_sub_admin_and_program(
        db_session, make_user, "PROGUPD"
    )
    resp = await client.patch(
        f"/api/v1/admin/programs/{other_program.id}",
        json={"total_semesters": 4},
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 403


async def test_sub_admin_cannot_delete_program_in_other_department(
    client, db_session, make_user, sub_admin
):
    _, _, other_program = await _other_department_with_sub_admin_and_program(
        db_session, make_user, "PROGDEL"
    )
    resp = await client.delete(
        f"/api/v1/admin/programs/{other_program.id}", headers=auth_header(sub_admin)
    )
    assert resp.status_code == 403


async def test_sub_admin_cannot_create_plo_in_other_departments_program(
    client, db_session, make_user, sub_admin
):
    _, _, other_program = await _other_department_with_sub_admin_and_program(
        db_session, make_user, "PLOCREATE"
    )
    resp = await client.post(
        "/api/v1/admin/plos",
        json={
            "program_id": other_program.id,
            "code": "PLO-BLOCKED",
            "title": "Blocked",
            "description": "Should not be creatable from another department.",
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 403


async def test_sub_admin_cannot_read_plo_owned_by_other_department(
    client, db_session, make_user, sub_admin
):
    _, other_sub_admin, other_program = await _other_department_with_sub_admin_and_program(
        db_session, make_user, "PLOREAD"
    )
    create_resp = await client.post(
        "/api/v1/admin/plos",
        json={
            "program_id": other_program.id,
            "code": "PLO-EXISTS",
            "title": "Exists",
            "description": "Owned by the other department.",
        },
        headers=auth_header(other_sub_admin),
    )
    assert create_resp.status_code == 201
    plo_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/admin/plos/{plo_id}", headers=auth_header(sub_admin))
    assert get_resp.status_code == 403


async def test_sub_admin_cannot_create_course_under_other_departments_program(
    client, db_session, make_user, sub_admin
):
    _, _, other_program = await _other_department_with_sub_admin_and_program(
        db_session, make_user, "COURSE"
    )
    resp = await client.post(
        "/api/v1/courses",
        json={
            "program_id": other_program.id,
            "code": "CS-BLOCKED",
            "name": "Blocked Course",
            "credit_hours": 3,
            "semester": 1,
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 403


# --- Tier boundaries: super_admin is departments/sub-admins only -----------


async def test_super_admin_cannot_list_programs(client, make_user):
    super_admin = await make_user("superadmin.noprog@adaptobe.edu", role=UserRole.super_admin)
    resp = await client.get("/api/v1/admin/programs", headers=auth_header(super_admin))
    assert resp.status_code == 403


async def test_super_admin_cannot_list_plos(client, make_user):
    super_admin = await make_user("superadmin.noplo@adaptobe.edu", role=UserRole.super_admin)
    resp = await client.get("/api/v1/admin/plos", headers=auth_header(super_admin))
    assert resp.status_code == 403


async def test_super_admin_cannot_list_courses(client, make_user):
    super_admin = await make_user("superadmin.nocourse@adaptobe.edu", role=UserRole.super_admin)
    resp = await client.get("/api/v1/courses", headers=auth_header(super_admin))
    assert resp.status_code == 403


# --- Tier boundaries: sub_admin is department-operational only -------------


async def test_sub_admin_cannot_list_departments(client, sub_admin):
    resp = await client.get("/api/v1/admin/departments", headers=auth_header(sub_admin))
    assert resp.status_code == 403


async def test_sub_admin_cannot_create_department(client, sub_admin):
    resp = await client.post(
        "/api/v1/admin/departments",
        json={"name": "New Dept", "code": "NEWDEPT"},
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 403


async def test_sub_admin_cannot_manage_another_sub_admin(client, make_user, sub_admin, department):
    other_sub_admin = await make_user(
        "subadmin.peer@adaptobe.edu",
        role=UserRole.sub_admin,
        dept_id=department.id,
        employee_id="EMP-PEER",
    )
    resp = await client.get(
        f"/api/v1/admin/users/{other_sub_admin.id}", headers=auth_header(sub_admin)
    )
    assert resp.status_code == 403


async def test_sub_admin_cannot_register_a_sub_admin(client, sub_admin, department):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sneaky.subadmin@adaptobe.edu",
            "password": "password123",
            "full_name": "Sneaky",
            "role": "sub_admin",
            "dept_id": department.id,
            "employee_id": "EMP-SNEAKY",
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 422


# --- Field validation: student registration ---------------------------------


async def test_student_registration_requires_enrollment_no(client, sub_admin):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "noenrollment@adaptobe.edu",
            "password": "password123",
            "full_name": "No Enrollment",
            "role": "student",
            "seat_no": "SEAT-1",
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 422


async def test_student_registration_requires_seat_no(client, sub_admin):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "noseat@adaptobe.edu",
            "password": "password123",
            "full_name": "No Seat",
            "role": "student",
            "enrollment_no": "ENR-1",
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 422


# --- Field validation: PLO Bloom Domain --------------------------------------


async def test_plo_creation_rejects_invalid_domain(client, sub_admin, program):
    resp = await client.post(
        "/api/v1/admin/plos",
        json={
            "program_id": program.id,
            "code": "PLO-BADDOMAIN",
            "title": "Bad Domain",
            "description": "Uses a domain value outside the allowed set.",
            "domain": "NotARealDomain",
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 422


async def test_plo_creation_accepts_valid_domain(client, sub_admin, program):
    resp = await client.post(
        "/api/v1/admin/plos",
        json={
            "program_id": program.id,
            "code": "PLO-GOODDOMAIN",
            "title": "Good Domain",
            "description": "Uses one of the three allowed Bloom domains.",
            "domain": "Psychomotor",
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 201


# --- Field validation: student father_name / faculty employee_id ("Faculty ID") ---


async def test_student_registration_requires_father_name(client, sub_admin):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "nofather@adaptobe.edu",
            "password": "password123",
            "full_name": "No Father",
            "role": "student",
            "enrollment_no": "ENR-NOFATHER",
            "seat_no": "SEAT-NOFATHER",
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 422


async def test_faculty_registration_requires_employee_id(client, sub_admin):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "nofacultyid@adaptobe.edu",
            "password": "password123",
            "full_name": "No Faculty ID",
            "role": "faculty",
        },
        headers=auth_header(sub_admin),
    )
    assert resp.status_code == 422


# --- Password reveal endpoint ------------------------------------------------


async def test_sub_admin_can_reveal_own_student_password(client, sub_admin, department):
    create_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "revealme@adaptobe.edu",
            "password": "RevealMe123!",
            "full_name": "Reveal Me",
            "role": "student",
            "enrollment_no": "ENR-REVEAL",
            "seat_no": "SEAT-REVEAL",
            "father_name": "Father Reveal",
        },
        headers=auth_header(sub_admin),
    )
    assert create_resp.status_code == 201
    student_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/admin/users/{student_id}/password", headers=auth_header(sub_admin)
    )
    assert resp.status_code == 200
    assert resp.json()["password"] == "RevealMe123!"


async def test_registration_without_password_generates_one(client, sub_admin, department):
    """The manual 'Add Student' form no longer sends a password -- omitting
    it entirely must still produce a working, revealable password."""
    create_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "autopassword@adaptobe.edu",
            "full_name": "Auto Password",
            "role": "student",
            "enrollment_no": "ENR-AUTOPW",
            "seat_no": "SEAT-AUTOPW",
            "father_name": "Father Autopw",
        },
        headers=auth_header(sub_admin),
    )
    assert create_resp.status_code == 201
    student_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/admin/users/{student_id}/password", headers=auth_header(sub_admin)
    )
    assert resp.status_code == 200
    password = resp.json()["password"]

    # Same criteria as app.core.security.generate_password: 8 chars, at
    # least one letter and one digit, no ambiguous glyphs.
    assert len(password) == 8
    assert any(c.isalpha() for c in password)
    assert any(c.isdigit() for c in password)
    assert not set(password) & set("0O1lI")

    login = await client.post(
        "/api/v1/auth/login", json={"email": "autopassword@adaptobe.edu", "password": password}
    )
    assert login.status_code == 200


async def test_password_never_appears_in_user_list(client, sub_admin, department):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "notleaked@adaptobe.edu",
            "password": "NotLeaked123!",
            "full_name": "Not Leaked",
            "role": "student",
            "enrollment_no": "ENR-NOTLEAKED",
            "seat_no": "SEAT-NOTLEAKED",
            "father_name": "Father Notleaked",
        },
        headers=auth_header(sub_admin),
    )

    resp = await client.get("/api/v1/admin/users", headers=auth_header(sub_admin))
    assert resp.status_code == 200
    assert "NotLeaked123!" not in resp.text
    assert all("password" not in user for user in resp.json())


async def test_sub_admin_cannot_reveal_password_of_user_in_other_department(
    client, db_session, make_user, sub_admin
):
    _, other_sub_admin, _ = await _other_department_with_sub_admin_and_program(
        db_session, make_user, "PWREVEAL"
    )
    other_student_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "otherdeptpw@adaptobe.edu",
            "password": "OtherDeptPw123!",
            "full_name": "Other Dept Student",
            "role": "student",
            "enrollment_no": "ENR-OTHERDEPTPW",
            "seat_no": "SEAT-OTHERDEPTPW",
            "father_name": "Father Otherdeptpw",
        },
        headers=auth_header(other_sub_admin),
    )
    assert other_student_resp.status_code == 201
    other_student_id = other_student_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/admin/users/{other_student_id}/password", headers=auth_header(sub_admin)
    )
    assert resp.status_code == 403


async def test_password_reveal_returns_null_for_legacy_account_without_encrypted_password(
    client, make_user, sub_admin, department, db_session
):
    from app.services.user_service import get_user

    student = await make_user(
        "legacypw@adaptobe.edu",
        role=UserRole.student,
        dept_id=department.id,
        enrollment_no="ENR-LEGACYPW",
        seat_no="SEAT-LEGACYPW",
        father_name="Father Legacypw",
    )
    # Simulate an account whose password was set outside app code (e.g. a
    # direct database update) -- no encrypted copy on file.
    persisted = await get_user(db_session, student.id)
    persisted.password_encrypted = None
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/admin/users/{student.id}/password", headers=auth_header(sub_admin)
    )
    assert resp.status_code == 200
    assert resp.json()["password"] is None
