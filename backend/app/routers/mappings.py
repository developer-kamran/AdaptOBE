from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.mapping import (
    MappingConfirmRequest,
    MappingRead,
    MappingSuggestRequest,
    MappingSuggestResponse,
)
from app.services import mapping_service
from app.services.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

router = APIRouter(prefix="/api/v1/mappings", tags=["mappings"])

# CLO-PLO mapping is a faculty-operational concern -- neither admin tier
# touches it, per the admin-hierarchy redesign.
FacultyOnly = Depends(require_roles(UserRole.faculty))


@router.post("/suggest", response_model=MappingSuggestResponse)
async def suggest(
    data: MappingSuggestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        suggestions = await mapping_service.suggest_plos(
            db, data.clo_id, current_user, data.limit
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    return MappingSuggestResponse(clo_id=data.clo_id, suggestions=suggestions)


@router.post("/confirm", response_model=MappingRead, status_code=status.HTTP_201_CREATED)
async def confirm(
    data: MappingConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        return await mapping_service.confirm_mapping(db, data, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/clo/{clo_id}", response_model=list[MappingRead])
async def list_for_clo(
    clo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        return await mapping_service.list_mappings_for_clo(db, clo_id, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        await mapping_service.delete_mapping(db, mapping_id, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
