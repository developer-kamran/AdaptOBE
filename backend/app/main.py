from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.routers import (
    assessments,
    attainment,
    auth,
    courses,
    departments,
    enrollments,
    mappings,
    plos,
    programs,
    student_import,
    students,
    users,
    ws,
)
from app.services import notifications


@asynccontextmanager
async def lifespan(app: FastAPI):
    notifications.subscribe(ws.forward_to_websockets)
    yield
    notifications.unsubscribe(ws.forward_to_websockets)


app = FastAPI(title="AdaptOBE API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(students.router)
app.include_router(student_import.router)
app.include_router(departments.router)
app.include_router(programs.router)
app.include_router(plos.router)
app.include_router(courses.router)
app.include_router(courses.clo_router)
app.include_router(enrollments.router)
app.include_router(mappings.router)
app.include_router(assessments.router)
app.include_router(attainment.router)
app.include_router(ws.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    vector_ext = await db.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    )
    return {
        "database": "connected" if result.scalar() == 1 else "error",
        "pgvector_enabled": vector_ext.scalar() is not None,
    }
