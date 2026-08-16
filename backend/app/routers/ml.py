from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.prediction import RiskPredictionReport, StoredPredictionReport
from app.services import risk_service
from app.services.exceptions import NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/api/v1/ml", tags=["ml"])

# Risk prediction is a teaching-workflow endpoint: faculty only, in line with
# the admin-hierarchy redesign that made attainment/scoring faculty-only too.
FacultyOnly = Depends(require_roles(UserRole.faculty))


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))


@router.post("/predict-risk/{course_id}", response_model=RiskPredictionReport)
async def predict_risk(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        return await risk_service.predict_course_risk(db, course_id, current_user)
    except (NotFoundError, PermissionDeniedError, ValidationError) as exc:
        raise _translate(exc) from exc


@router.get("/predict-risk/{course_id}", response_model=StoredPredictionReport)
async def stored_risk(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOnly,
):
    try:
        return await risk_service.get_stored_predictions(db, course_id, current_user)
    except (NotFoundError, PermissionDeniedError) as exc:
        raise _translate(exc) from exc
