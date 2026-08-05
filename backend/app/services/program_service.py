from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.program import Program
from app.schemas.program import ProgramCreate, ProgramUpdate
from app.services.exceptions import ConflictError, NotFoundError


async def list_programs(db: AsyncSession) -> list[Program]:
    result = await db.execute(select(Program).order_by(Program.id))
    return list(result.scalars().all())


async def get_program(db: AsyncSession, program_id: int) -> Program:
    program = await db.get(Program, program_id)
    if program is None:
        raise NotFoundError(f"Program {program_id} not found")
    return program


CONFLICT_MESSAGE = "A programme with this code already exists, or the department reference is invalid"


async def get_program_by_code(db: AsyncSession, code: str) -> Program | None:
    result = await db.execute(select(Program).where(Program.code == code))
    return result.scalar_one_or_none()


async def create_program(db: AsyncSession, data: ProgramCreate) -> Program:
    program = Program(
        dept_id=data.dept_id,
        code=data.code,
        name=data.name,
        total_semesters=data.total_semesters,
    )
    db.add(program)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(CONFLICT_MESSAGE) from exc

    await db.refresh(program)
    return program


async def update_program(db: AsyncSession, program_id: int, data: ProgramUpdate) -> Program:
    program = await get_program(db, program_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(program, field, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(CONFLICT_MESSAGE) from exc

    await db.refresh(program)
    return program


async def delete_program(db: AsyncSession, program_id: int) -> None:
    program = await get_program(db, program_id)
    await db.delete(program)
    await db.commit()
