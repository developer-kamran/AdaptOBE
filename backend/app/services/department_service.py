from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.exceptions import ConflictError, NotFoundError


async def list_departments(db: AsyncSession) -> list[Department]:
    result = await db.execute(select(Department).order_by(Department.id))
    return list(result.scalars().all())


async def get_department(db: AsyncSession, department_id: int) -> Department:
    department = await db.get(Department, department_id)
    if department is None:
        raise NotFoundError(f"Department {department_id} not found")
    return department


async def create_department(db: AsyncSession, data: DepartmentCreate) -> Department:
    department = Department(name=data.name, code=data.code)
    db.add(department)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A department with this code already exists") from exc

    await db.refresh(department)
    return department


async def update_department(db: AsyncSession, department_id: int, data: DepartmentUpdate) -> Department:
    department = await get_department(db, department_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(department, field, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A department with this code already exists") from exc

    await db.refresh(department)
    return department


async def delete_department(db: AsyncSession, department_id: int) -> None:
    department = await get_department(db, department_id)
    await db.delete(department)
    await db.commit()
