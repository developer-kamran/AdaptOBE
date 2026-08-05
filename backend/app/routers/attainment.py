from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.course import Course
from app.models.user import User, UserRole
from app.schemas.attainment import CourseAttainmentReport, StudentProgressReport
from app.services import attainment_service, course_service, report_service
from app.services.exceptions import NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api/v1/attainment", tags=["attainment"])

FacultyOrAdmin = Depends(require_roles(UserRole.faculty, UserRole.admin))


async def _course_for_user(db: AsyncSession, course_id: int, user: User) -> Course:
    try:
        return await course_service.get_course_for_user(db, course_id, user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/course/{course_id}", response_model=CourseAttainmentReport)
async def course_attainment(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    await _course_for_user(db, course_id, current_user)
    return await attainment_service.build_course_report(db, course_id)


@router.post("/course/{course_id}/recalculate", response_model=CourseAttainmentReport)
async def recalculate(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    await _course_for_user(db, course_id, current_user)
    await attainment_service.recalculate_course_attainment(db, course_id)
    return await attainment_service.build_course_report(db, course_id)


@router.get(
    "/course/{course_id}/student/{student_id}", response_model=StudentProgressReport
)
async def student_attainment(
    course_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    await _course_for_user(db, course_id, current_user)
    return await attainment_service.build_student_report(db, course_id, student_id)


@router.get("/course/{course_id}/export/pdf")
async def export_pdf(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    course = await _course_for_user(db, course_id, current_user)
    report = await attainment_service.build_course_report(db, course_id)
    pdf_bytes = report_service.build_pdf_report(course, report)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{course.code}-attainment.pdf"'
        },
    )


@router.get("/course/{course_id}/export/excel")
async def export_excel(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = FacultyOrAdmin,
):
    course = await _course_for_user(db, course_id, current_user)
    report = await attainment_service.build_course_report(db, course_id)
    excel_bytes = report_service.build_excel_report(course, report)

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{course.code}-attainment.xlsx"'
        },
    )
