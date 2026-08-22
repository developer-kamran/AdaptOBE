"""Attendance-sheet import: file -> preview -> confirmed attendance.

Mirrors `enrollment_import_service.py`'s preview/confirm split. `confirm`
delegates to the existing `attendance_service.bulk_set_attendance` -- no
parallel write path, so its own enrollment-membership + range validation
applies at commit time too, as defense in depth.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import column_matcher
from app.models.course import Course
from app.models.user import User
from app.schemas.attendance_import import (
    FIELD_LABELS,
    REQUIRED_FIELDS,
    AttendanceImportPreview,
    ExtractedAttendanceRow,
)
from app.services import enrollment_service, file_parsers


def _value_at(row: list[str], index: int | None) -> str | None:
    if index is None or index >= len(row):
        return None
    value = row[index].strip()
    return value or None


async def build_preview(
    db: AsyncSession, course: Course, content: bytes, filename: str
) -> AttendanceImportPreview:
    rows = file_parsers.parse_file(content, filename)
    warnings: list[str] = []

    if not rows:
        return AttendanceImportPreview(
            total_detected=0,
            ready_count=0,
            student_not_found_count=0,
            duplicate_count=0,
            invalid_percentage_count=0,
            records=[],
            detected_columns={field: None for field in REQUIRED_FIELDS},
            warnings=[
                "No table could be detected in this file. For PDFs, the sheet "
                "must be a real table rather than free text."
            ],
        )

    header_row, *data_rows = rows
    detected = await column_matcher.match_columns(
        header_row, column_matcher.ATTENDANCE_FIELD_PROMPTS, column_matcher.ATTENDANCE_ALIASES
    )
    detected_columns = {
        field: (header_row[index] if index is not None and index < len(header_row) else None)
        for field, index in detected.items()
    }

    unmatched = [FIELD_LABELS[f] for f in REQUIRED_FIELDS if detected.get(f) is None]
    if unmatched:
        warnings.append(
            f"These columns could not be found in the file, so matching may be incomplete: {', '.join(unmatched)}"
        )

    raw_rows: list[dict[str, str | None]] = []
    for offset, row in enumerate(data_rows, start=2):
        record = {
            "row_number": offset,
            "full_name": _value_at(row, detected.get("full_name")),
            "father_name": _value_at(row, detected.get("father_name")),
            "seat_no": _value_at(row, detected.get("seat_no")),
            "attendance_percentage_raw": _value_at(row, detected.get("attendance_percentage")),
        }
        if not any(record[f] for f in ("full_name", "father_name", "seat_no")):
            continue  # spacing/footer noise
        raw_rows.append(record)

    # Roster-scoped, not all students -- a seat_no that's valid elsewhere but
    # not enrolled in *this* course is still not_found here.
    student_ids = await enrollment_service.list_enrolled_student_ids(db, course.id)
    roster = list(
        (await db.execute(select(User).where(User.id.in_(student_ids or [0])))).scalars().all()
    )
    by_seat_no = {s.seat_no: s for s in roster if s.seat_no}
    by_full_name = {s.full_name.strip().lower(): s for s in roster if s.full_name}

    seen_seat_nos: set[str] = set()
    seen_names: set[str] = set()
    records: list[ExtractedAttendanceRow] = []

    for raw in raw_rows:
        record = ExtractedAttendanceRow(
            row_number=raw["row_number"],
            full_name=raw["full_name"],
            father_name=raw["father_name"],
            seat_no=raw["seat_no"],
            attendance_percentage_raw=raw["attendance_percentage_raw"],
            matched_student_id=None,
        )

        is_duplicate = (record.seat_no is not None and record.seat_no in seen_seat_nos) or (
            record.full_name is not None and record.full_name.strip().lower() in seen_names
        )
        if record.seat_no:
            seen_seat_nos.add(record.seat_no)
        if record.full_name:
            seen_names.add(record.full_name.strip().lower())

        matched = by_seat_no.get(record.seat_no) if record.seat_no else None
        if matched is None and record.full_name:
            matched = by_full_name.get(record.full_name.strip().lower())

        percentage: float | None = None
        if record.attendance_percentage_raw is not None:
            try:
                percentage = float(record.attendance_percentage_raw)
            except ValueError:
                percentage = None

        if is_duplicate:
            record.status = "duplicate_in_file"
            record.detail = "This student appears more than once in the file"
        elif matched is None:
            record.status = "student_not_found"
            record.detail = "No student enrolled in this course matches this name/seat number"
        else:
            record.matched_student_id = matched.id
            if percentage is None or percentage < 0 or percentage > 100:
                record.status = "invalid_percentage"
                record.detail = (
                    f"{record.attendance_percentage_raw!r} is not a valid 0-100 percentage"
                    if record.attendance_percentage_raw
                    else "No attendance percentage was found for this row"
                )
            else:
                record.status = "ready"

        records.append(record)

    def _count(status: str) -> int:
        return sum(1 for r in records if r.status == status)

    return AttendanceImportPreview(
        total_detected=len(records),
        ready_count=_count("ready"),
        student_not_found_count=_count("student_not_found"),
        duplicate_count=_count("duplicate_in_file"),
        invalid_percentage_count=_count("invalid_percentage"),
        records=records,
        detected_columns=detected_columns,
        warnings=warnings,
    )
