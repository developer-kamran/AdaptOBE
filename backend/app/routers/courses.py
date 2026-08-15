from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.clo import CLOCreate, CLORead, CLOUpdate
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate
from app.services import clo_service, course_service
from app.services.exceptions import ConflictError, NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api/v1/courses", tags=["courses"])

# Faculty own and manage their own courses; a sub_admin manages every course
# in their own department (via the course's programme -- see ensure_can_manage).
FacultyOrSubAdmin = Depends(require_roles(UserRole.faculty, UserRole.sub_admin))


def _not_found(exc: NotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _forbidden(exc: PermissionDeniedError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("", response_model=list[CourseRead])
async def list_courses(
    mine: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    owner_id = current_user.id if mine else None
    return await course_service.list_courses(db, owner_id, current_user)


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    try:
        return await course_service.create_course(db, data, current_user)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise _forbidden(exc) from exc


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    try:
        return await course_service.get_course_for_user(db, course_id, current_user)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    except PermissionDeniedError as exc:
        raise _forbidden(exc) from exc


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: int,
    data: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    try:
        return await course_service.update_course(db, course_id, data, current_user)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    except PermissionDeniedError as exc:
        raise _forbidden(exc) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    try:
        await course_service.delete_course(db, course_id, current_user)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    except PermissionDeniedError as exc:
        raise _forbidden(exc) from exc


@router.get("/{course_id}/clos", response_model=list[CLORead])
async def list_clos(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    try:
        await course_service.get_course_for_user(db, course_id, current_user)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    except PermissionDeniedError as exc:
        raise _forbidden(exc) from exc

    return await clo_service.list_clos(db, course_id)


@router.post("/{course_id}/clos", response_model=CLORead, status_code=status.HTTP_201_CREATED)
async def create_clo(
    course_id: int,
    data: CLOCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    try:
        return await clo_service.create_clo(db, course_id, data, current_user)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    except PermissionDeniedError as exc:
        raise _forbidden(exc) from exc


clo_router = APIRouter(prefix="/api/v1/clos", tags=["clos"])


@clo_router.get("/{clo_id}", response_model=CLORead)
async def get_clo(
    clo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    try:
        clo = await clo_service.get_clo(db, clo_id)
        await course_service.get_course_for_user(db, clo.course_id, current_user)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    except PermissionDeniedError as exc:
        raise _forbidden(exc) from exc
    return clo


@clo_router.patch("/{clo_id}", response_model=CLORead)
async def update_clo(
    clo_id: int,
    data: CLOUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    try:
        return await clo_service.update_clo(db, clo_id, data, current_user)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    except PermissionDeniedError as exc:
        raise _forbidden(exc) from exc


@clo_router.delete("/{clo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clo(
    clo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrSubAdmin,
):
    try:
        await clo_service.delete_clo(db, clo_id, current_user)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    except PermissionDeniedError as exc:
        raise _forbidden(exc) from exc
