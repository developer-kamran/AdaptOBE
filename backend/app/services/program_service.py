from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.program import Program
from app.models.user import User, UserRole
from app.schemas.program import ProgramCreate, ProgramUpdate
from app.services.exceptions import ConflictError, NotFoundError, PermissionDeniedError


async def list_programs(db: AsyncSession, current_user: User) -> list[Program]:
    stmt = select(Program).order_by(Program.id)
    if current_user.role == UserRole.sub_admin:
        stmt = stmt.where(Program.dept_id == current_user.dept_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_program(db: AsyncSession, program_id: int) -> Program:
    program = await db.get(Program, program_id)
    if program is None:
        raise NotFoundError(f"Program {program_id} not found")
    return program


def ensure_can_manage_program(current_user: User, program: Program) -> None:
    if current_user.role == UserRole.sub_admin and program.dept_id != current_user.dept_id:
        raise PermissionDeniedError("You do not have permission to manage this programme")


async def get_program_scoped(db: AsyncSession, program_id: int, current_user: User) -> Program:
    program = await get_program(db, program_id)
    ensure_can_manage_program(current_user, program)
    return program


CONFLICT_MESSAGE = "A programme with this code already exists, or the department reference is invalid"


async def get_program_by_code(db: AsyncSession, code: str) -> Program | None:
    result = await db.execute(select(Program).where(Program.code == code))
    return result.scalar_one_or_none()


async def create_program(db: AsyncSession, data: ProgramCreate, current_user: User) -> Program:
    # A sub_admin can only ever create programmes in their own department --
    # ignore/override whatever dept_id was submitted, same pattern as user
    # creation. Nothing else may create programmes (route is sub_admin-only).
    dept_id = current_user.dept_id if current_user.role == UserRole.sub_admin else data.dept_id

    program = Program(
        dept_id=dept_id,
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


async def update_program(
    db: AsyncSession, program_id: int, data: ProgramUpdate, current_user: User
) -> Program:
    program = await get_program_scoped(db, program_id, current_user)

    changes = data.model_dump(exclude_unset=True)
    if current_user.role == UserRole.sub_admin:
        # A sub_admin cannot move a programme to another department.
        changes.pop("dept_id", None)

    for field, value in changes.items():
        setattr(program, field, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(CONFLICT_MESSAGE) from exc

    await db.refresh(program)
    return program


async def delete_program(db: AsyncSession, program_id: int, current_user: User) -> None:
    program = await get_program_scoped(db, program_id, current_user)
    await db.delete(program)
    await db.commit()
