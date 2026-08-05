from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mapping import CloPloMapping
from app.models.plo import PLO
from app.models.user import User
from app.schemas.mapping import MappingConfirmRequest, PLOSuggestion
from app.services import clo_service, course_service, plo_service
from app.services.exceptions import ConflictError, NotFoundError, ValidationError


async def suggest_plos(
    db: AsyncSession, clo_id: int, user: User, limit: int = 3
) -> list[PLOSuggestion]:
    """Rank the PLOs of the CLO's own program by semantic closeness to that CLO.

    Uses pgvector's `<=>` cosine-distance operator. Note that CLAUDE.md section 10
    names the `<->` operator for this, but in pgvector `<->` is L2 distance while
    `<=>` is cosine distance -- and the spec's stated intent (sections 9 and 7) is
    cosine similarity, so `<=>` is what is used here. Embeddings are normalized at
    encode time, so the two rank identically regardless.
    """
    clo = await clo_service.get_clo(db, clo_id)
    course = await course_service.get_course_for_user(db, clo.course_id, user)

    if clo.embedding is None:
        raise ValidationError(f"CLO {clo_id} has no embedding to compare against")

    distance = PLO.embedding.cosine_distance(clo.embedding).label("distance")
    stmt = (
        select(PLO, distance)
        .where(PLO.program_id == course.program_id, PLO.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    rows = await db.execute(stmt)

    return [
        PLOSuggestion(
            plo_id=plo.id,
            code=plo.code,
            title=plo.title,
            description=plo.description,
            similarity_score=round(1.0 - float(dist), 6),
        )
        for plo, dist in rows.all()
    ]


async def confirm_mapping(
    db: AsyncSession, data: MappingConfirmRequest, user: User
) -> CloPloMapping:
    """Create or update the mapping between a CLO and a PLO.

    Confirming an existing pair updates it rather than erroring, so faculty can
    revise a strength they already set.
    """
    clo = await clo_service.get_clo(db, data.clo_id)
    course = await course_service.get_course_for_user(db, clo.course_id, user)
    plo = await plo_service.get_plo(db, data.plo_id)

    if plo.program_id != course.program_id:
        raise ValidationError("CLO and PLO must belong to the same program")

    result = await db.execute(
        select(CloPloMapping).where(
            CloPloMapping.clo_id == data.clo_id, CloPloMapping.plo_id == data.plo_id
        )
    )
    mapping = result.scalar_one_or_none()

    if mapping is None:
        mapping = CloPloMapping(
            clo_id=data.clo_id,
            plo_id=data.plo_id,
            strength=data.strength,
            is_ai_generated=data.is_ai_generated,
            similarity_score=data.similarity_score,
        )
        db.add(mapping)
    else:
        mapping.strength = data.strength
        mapping.is_ai_generated = data.is_ai_generated
        mapping.similarity_score = data.similarity_score

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("This CLO-PLO mapping could not be saved") from exc

    await db.refresh(mapping)
    return mapping


async def list_mappings_for_clo(
    db: AsyncSession, clo_id: int, user: User
) -> list[CloPloMapping]:
    clo = await clo_service.get_clo(db, clo_id)
    await course_service.get_course_for_user(db, clo.course_id, user)

    result = await db.execute(
        select(CloPloMapping)
        .where(CloPloMapping.clo_id == clo_id)
        .order_by(CloPloMapping.id)
    )
    return list(result.scalars().all())


async def delete_mapping(db: AsyncSession, mapping_id: int, user: User) -> None:
    mapping = await db.get(CloPloMapping, mapping_id)
    if mapping is None:
        raise NotFoundError(f"Mapping {mapping_id} not found")

    clo = await clo_service.get_clo(db, mapping.clo_id)
    await course_service.get_course_for_user(db, clo.course_id, user)

    await db.delete(mapping)
    await db.commit()
