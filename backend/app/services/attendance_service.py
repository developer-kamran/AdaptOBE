"""Faculty-entered attendance, the one XGBoost feature with no other source.

Attendance is stored as a single percentage per (course, student). The risk
service reads it through `attendance_map`; faculty maintain it through the
bulk-upsert path, exactly like score entry.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceRecord
from app.schemas.attendance import BulkAttendanceRequest
from app.services import course_service, enrollment_service
from app.services.exceptions import ValidationError


async def list_attendance(db: AsyncSession, course_id: int) -> list[AttendanceRecord]:
    result = await db.execute(
        select(AttendanceRecord)
        .where(AttendanceRecord.course_id == course_id)
        .order_by(AttendanceRecord.student_id)
    )
    return list(result.scalars().all())


async def attendance_map(db: AsyncSession, course_id: int) -> dict[int, float]:
    """student_id -> attendance_percentage for a course (feature lookup)."""
    records = await list_attendance(db, course_id)
    return {record.student_id: record.attendance_percentage for record in records}


async def bulk_set_attendance(
    db: AsyncSession, course_id: int, data: BulkAttendanceRequest, user
) -> int:
    """Validate and upsert a batch of attendance percentages.

    The whole batch is validated before anything is written, so one bad row
    cannot leave attendance half-entered (same discipline as bulk scoring).
    Returns the number of rows saved.
    """
    await course_service.get_course_for_user(db, course_id, user)

    enrolled = set(await enrollment_service.list_enrolled_student_ids(db, course_id))
    for entry in data.entries:
        if entry.student_id not in enrolled:
            raise ValidationError(
                f"Student {entry.student_id} is not enrolled in this course"
            )

    existing = {record.student_id: record for record in await list_attendance(db, course_id)}
    for entry in data.entries:
        record = existing.get(entry.student_id)
        if record is not None:
            record.attendance_percentage = entry.attendance_percentage
        else:
            db.add(
                AttendanceRecord(
                    course_id=course_id,
                    student_id=entry.student_id,
                    attendance_percentage=entry.attendance_percentage,
                )
            )

    await db.commit()
    return len(data.entries)
