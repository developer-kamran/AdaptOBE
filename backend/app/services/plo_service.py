from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import embeddings
from app.models.plo import PLO
from app.schemas.plo import PLOCreate, PLOUpdate
from app.services.exceptions import ConflictError, NotFoundError


def build_embedding_source(title: str, description: str) -> str:
    """Text fed to the encoder. Title plus description gives the model more signal."""
    return f"{title}. {description}"


async def list_plos(db: AsyncSession, program_id: int | None = None) -> list[PLO]:
    stmt = select(PLO).order_by(PLO.id)
    if program_id is not None:
        stmt = stmt.where(PLO.program_id == program_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_plo(db: AsyncSession, plo_id: int) -> PLO:
    plo = await db.get(PLO, plo_id)
    if plo is None:
        raise NotFoundError(f"PLO {plo_id} not found")
    return plo


async def create_plo(db: AsyncSession, data: PLOCreate) -> PLO:
    embedding = await embeddings.aencode_text(
        build_embedding_source(data.title, data.description)
    )

    plo = PLO(
        program_id=data.program_id,
        code=data.code,
        title=data.title,
        description=data.description,
        domain=data.domain,
        embedding=embedding,
    )
    db.add(plo)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Invalid program reference for this PLO") from exc

    await db.refresh(plo)
    return plo


async def update_plo(db: AsyncSession, plo_id: int, data: PLOUpdate) -> PLO:
    plo = await get_plo(db, plo_id)

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(plo, field, value)

    # Title/description drive the embedding, so regenerate when either changes.
    if "title" in changes or "description" in changes:
        plo.embedding = await embeddings.aencode_text(
            build_embedding_source(plo.title, plo.description)
        )

    await db.commit()
    await db.refresh(plo)
    return plo


async def delete_plo(db: AsyncSession, plo_id: int) -> None:
    plo = await get_plo(db, plo_id)
    await db.delete(plo)
    await db.commit()
