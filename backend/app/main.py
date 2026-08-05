from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

app = FastAPI(title="AdaptOBE API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
