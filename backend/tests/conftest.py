import math
import re
import zlib

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.ml import embeddings
from app.models.assessment import AssessmentType
from app.models.user import User, UserRole
from app.schemas.assessment import AssessmentCreate
from app.schemas.clo import CLOCreate
from app.schemas.course import CourseCreate
from app.schemas.department import DepartmentCreate
from app.schemas.plo import PLOCreate
from app.schemas.program import ProgramCreate
from app.schemas.question import QuestionCreate
from app.schemas.score import BulkScoreRequest, ScoreEntry
from app.schemas.user import UserCreate
from app.services import (
    assessment_service,
    auth_service,
    clo_service,
    course_service,
    department_service,
    enrollment_service,
    plo_service,
    program_service,
    question_service,
    score_service,
)

# A dedicated NullPool engine avoids reusing pooled asyncpg connections
# across the different event loops pytest-asyncio spins up per test.
test_engine = create_async_engine(settings.database_url, poolclass=NullPool)


@pytest_asyncio.fixture
async def db_session():
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            class_=AsyncSession,
            join_transaction_mode="create_savepoint",
        )
        async with session_factory() as session:
            yield session
        await trans.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def make_user(db_session):
    async def _make_user(
        email: str,
        password: str = "password123",
        full_name: str = "Test User",
        role: UserRole = UserRole.student,
        **kwargs,
    ) -> User:
        data = UserCreate(email=email, password=password, full_name=full_name, role=role, **kwargs)
        return await auth_service.register_user(db_session, data)

    return _make_user


def auth_header(user: User) -> dict:
    token = create_access_token(str(user.id), user.role.value)
    return {"Authorization": f"Bearer {token}"}


def fake_encode(text: str) -> list[float]:
    """Deterministic stand-in for all-MiniLM-L6-v2.

    Hashes each word into one of the 384 dimensions and L2-normalizes the result,
    so texts sharing vocabulary genuinely score closer under cosine distance.
    That keeps ranking assertions meaningful without loading PyTorch in tests.
    """
    vector = [0.0] * embeddings.EMBEDDING_DIM
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        vector[zlib.crc32(word.encode()) % embeddings.EMBEDDING_DIM] += 1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


@pytest.fixture(autouse=True)
def stub_encoder(monkeypatch):
    """Keep the real model out of the test suite; `aencode_text` resolves this at call time."""
    monkeypatch.setattr(embeddings, "encode_text", fake_encode)


@pytest_asyncio.fixture
async def program(db_session):
    department = await department_service.create_department(
        db_session, DepartmentCreate(name="Computer Science", code="CS-TEST")
    )
    return await program_service.create_program(
        db_session,
        ProgramCreate(
            dept_id=department.id,
            code="BSCS-TEST",
            name="BS Computer Science",
            total_semesters=8,
        ),
    )


@pytest_asyncio.fixture
async def faculty(make_user):
    return await make_user("faculty.owner@adaptobe.edu", role=UserRole.faculty)


@pytest_asyncio.fixture
async def course(db_session, program, faculty):
    return await course_service.create_course(
        db_session,
        CourseCreate(
            program_id=program.id,
            code="CS-101",
            name="Introduction to Programming",
            credit_hours=3,
            semester=1,
        ),
        faculty,
    )


@pytest_asyncio.fixture
async def make_plo(db_session, program):
    async def _make_plo(code: str, title: str, description: str, program_id: int | None = None):
        return await plo_service.create_plo(
            db_session,
            PLOCreate(
                program_id=program_id if program_id is not None else program.id,
                code=code,
                title=title,
                description=description,
            ),
        )

    return _make_plo


@pytest_asyncio.fixture
async def make_clo(db_session, course, faculty):
    async def _make_clo(code: str, title: str, description: str, course_id: int | None = None):
        return await clo_service.create_clo(
            db_session,
            course_id if course_id is not None else course.id,
            CLOCreate(code=code, title=title, description=description),
            faculty,
        )

    return _make_clo


@pytest_asyncio.fixture
async def make_student(make_user):
    async def _make_student(suffix: str, **kwargs):
        return await make_user(
            f"student.{suffix}@adaptobe.edu",
            full_name=f"Student {suffix}",
            role=UserRole.student,
            **kwargs,
        )

    return _make_student


@pytest_asyncio.fixture
async def enroll(db_session, course, faculty):
    async def _enroll(*students, course_id: int | None = None):
        return await enrollment_service.enroll_students(
            db_session,
            course_id if course_id is not None else course.id,
            [student.id for student in students],
            faculty,
        )

    return _enroll


@pytest_asyncio.fixture
async def make_assessment(db_session, course, faculty):
    async def _make_assessment(
        title: str = "Quiz 1",
        assessment_type: AssessmentType = AssessmentType.quiz,
        total_marks: float = 10.0,
        weightage_percent: float = 10.0,
        course_id: int | None = None,
    ):
        return await assessment_service.create_assessment(
            db_session,
            AssessmentCreate(
                course_id=course_id if course_id is not None else course.id,
                title=title,
                type=assessment_type,
                total_marks=total_marks,
                weightage_percent=weightage_percent,
            ),
            faculty,
        )

    return _make_assessment


@pytest_asyncio.fixture
async def make_question(db_session, faculty):
    async def _make_question(
        assessment_id: int,
        question_number: int,
        marks: float,
        clo_id: int | None = None,
        text: str | None = None,
    ):
        return await question_service.create_question(
            db_session,
            assessment_id,
            QuestionCreate(
                question_number=question_number, marks=marks, clo_id=clo_id, text=text
            ),
            faculty,
        )

    return _make_question


@pytest_asyncio.fixture
async def enter_scores(db_session, faculty):
    async def _enter_scores(assessment_id: int, entries: list[tuple[int, int, float]]):
        """entries: list of (question_id, student_id, marks_obtained)."""
        return await score_service.bulk_enter_scores(
            db_session,
            assessment_id,
            BulkScoreRequest(
                scores=[
                    ScoreEntry(question_id=q, student_id=s, marks_obtained=m)
                    for q, s, m in entries
                ]
            ),
            faculty,
        )

    return _enter_scores
