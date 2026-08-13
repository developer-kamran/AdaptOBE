from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import embeddings
from app.models.clo import CLO
from app.models.user import User
from app.schemas.clo import CLOCreate, CLOUpdate
from app.services import attainment_service, course_service
from app.services.exceptions import NotFoundError


def build_embedding_source(title: str, description: str) -> str:
    return f"{title}. {description}"


async def list_clos(db: AsyncSession, course_id: int) -> list[CLO]:
    result = await db.execute(select(CLO).where(CLO.course_id == course_id).order_by(CLO.id))
    return list(result.scalars().all())


async def get_clo(db: AsyncSession, clo_id: int) -> CLO:
    clo = await db.get(CLO, clo_id)
    if clo is None:
        raise NotFoundError(f"CLO {clo_id} not found")
    return clo


async def create_clo(db: AsyncSession, course_id: int, data: CLOCreate, user: User) -> CLO:
    await course_service.get_course_for_user(db, course_id, user)

    embedding = await embeddings.aencode_text(
        build_embedding_source(data.title, data.description)
    )

    clo = CLO(
        course_id=course_id,
        code=data.code,
        title=data.title,
        description=data.description,
        bloom_level=data.bloom_level,
        embedding=embedding,
    )
    db.add(clo)
    await db.commit()
    await db.refresh(clo)
    return clo


async def update_clo(db: AsyncSession, clo_id: int, data: CLOUpdate, user: User) -> CLO:
    clo = await get_clo(db, clo_id)
    await course_service.get_course_for_user(db, clo.course_id, user)

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(clo, field, value)

    if "title" in changes or "description" in changes:
        clo.embedding = await embeddings.aencode_text(
            build_embedding_source(clo.title, clo.description)
        )

    await db.commit()
    await db.refresh(clo)
    return clo


async def delete_clo(db: AsyncSession, clo_id: int, user: User) -> None:
    clo = await get_clo(db, clo_id)
    course_id = clo.course_id
    await course_service.get_course_for_user(db, course_id, user)
    await db.delete(clo)
    await db.commit()

    # Deleting a CLO untags any questions that pointed at it (SET NULL) and
    # cascade-deletes its CLO-PLO mappings, both of which change attainment.
    await attainment_service.recalculate_course_attainment(db, course_id)
