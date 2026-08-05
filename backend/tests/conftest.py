import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.services import auth_service

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
