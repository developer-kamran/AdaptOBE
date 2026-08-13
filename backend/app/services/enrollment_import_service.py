"""Course-enrollment roster import: file -> preview -> confirmed enrollment.

Mirrors the preview/confirm split in `student_import_service.py` (`build_preview`
touches no database), but this flow matches rows to *existing* student
accounts and enrolls them -- it never creates an account. See
`schemas/enrollment_import.py` for why.
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.institution import expected_seat_no_prefix
from app.ml import column_matcher
from app.models.course import Course
from app.models.program import Program
from app.models.user import User, UserRole
from app.schemas.enrollment_import import (
    FIELD_LABELS,
    REQUIRED_FIELDS,
    EnrollImportPreview,
    ExtractedEnrollmentRow,
)
from app.services import enrollment_service, file_parsers

_ELIGIBLE_TRUE = {"yes", "y", "true", "1", "eligible"}
_ELIGIBLE_FALSE = {"no", "n", "false", "0", "ineligible", "not eligible"}


def _value_at(row: list[str], index: int | None) -> str | None:
    if index is None or index >= len(row):
        return None
    value = row[index].strip()
    return value or None


def _parse_eligible(raw: str | None) -> bool | None:
    """None means "couldn't tell" -- treated the same as False by the
    caller (not added), but reported with its own message so the faculty
    knows to fix the file rather than assuming the student was rejected."""
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized in _ELIGIBLE_TRUE:
        return True
    if normalized in _ELIGIBLE_FALSE:
        return False
    return None


async def build_preview(
    db: AsyncSession, course: Course, content: bytes, filename: str
) -> EnrollImportPreview:
    """Parse and classify an uploaded roster against existing student
    accounts. Reads the database (to match/classify) but writes nothing."""
    rows = file_parsers.parse_file(content, filename)
    warnings: list[str] = []

    if not rows:
        return EnrollImportPreview(
            total_detected=0,
            ready_count=0,
            ineligible_count=0,
            not_found_count=0,
            wrong_programme_count=0,
            already_enrolled_count=0,
            duplicate_count=0,
            records=[],
            detected_columns={field: None for field in REQUIRED_FIELDS},
            warnings=[
                "No table could be detected in this file. For PDFs, the roster "
                "must be a real table rather than free text."
            ],
        )

    header_row, *data_rows = rows
    detected = await column_matcher.match_columns(
        header_row,
        column_matcher.ENROLLMENT_FIELD_PROMPTS,
        column_matcher.ENROLLMENT_ALIASES,
    )
    detected_columns = {
        field: (header_row[index] if index is not None and index < len(header_row) else None)
        for field, index in detected.items()
    }

    unmatched = [FIELD_LABELS[f] for f in REQUIRED_FIELDS if detected.get(f) is None]
    if unmatched:
        warnings.append(
            "These columns could not be found in the file, so matching may be "
            f"incomplete: {', '.join(unmatched)}"
        )

    # Pull every candidate row's raw fields first, so we can batch-lookup
    # matching accounts in one query rather than one per row.
    raw_rows: list[dict[str, str | None]] = []
    for offset, row in enumerate(data_rows, start=2):  # row 1 is the header
        record = {
            "row_number": offset,
            "full_name": _value_at(row, detected.get("full_name")),
            "father_name": _value_at(row, detected.get("father_name")),
            "enrollment_no": _value_at(row, detected.get("enrollment_no")),
            "seat_no": _value_at(row, detected.get("seat_no")),
            "eligible_raw": _value_at(row, detected.get("eligible")),
        }
        if not any(record[f] for f in ("full_name", "father_name", "enrollment_no", "seat_no")):
            continue  # spacing/footer noise
        raw_rows.append(record)

    enrollment_nos = {r["enrollment_no"] for r in raw_rows if r["enrollment_no"]}
    seat_nos = {r["seat_no"] for r in raw_rows if r["seat_no"]}

    matched_students: list[User] = []
    if enrollment_nos or seat_nos:
        stmt = select(User).where(User.role == UserRole.student)
        conditions = []
        if enrollment_nos:
            conditions.append(User.enrollment_no.in_(enrollment_nos))
        if seat_nos:
            conditions.append(User.seat_no.in_(seat_nos))
        stmt = stmt.where(or_(*conditions))
        matched_students = list((await db.execute(stmt)).scalars().all())

    by_enrollment_no = {s.enrollment_no: s for s in matched_students if s.enrollment_no}
    by_seat_no = {s.seat_no: s for s in matched_students if s.seat_no}

    program_code = (
        await db.execute(select(Program.code).where(Program.id == course.program_id))
    ).scalar_one_or_none()
    # Current-batch prefix for this course's programme + semester, e.g.
    # "B241101" for a BSSE course in semester 4 during 2026. This import
    # flow is for regular (non-backlog) enrollment -- backlog students go
    # through the dedicated "Add Backlog Student" flow instead.
    programme_prefix = expected_seat_no_prefix(program_code, course.semester) if program_code else None

    already_enrolled_ids = set(await enrollment_service.list_enrolled_student_ids(db, course.id))

    seen_enrollment_nos: set[str] = set()
    seen_seat_nos: set[str] = set()
    records: list[ExtractedEnrollmentRow] = []

    for raw in raw_rows:
        eligible = _parse_eligible(raw["eligible_raw"])
        record = ExtractedEnrollmentRow(
            row_number=raw["row_number"],
            full_name=raw["full_name"],
            father_name=raw["father_name"],
            enrollment_no=raw["enrollment_no"],
            seat_no=raw["seat_no"],
            eligible=eligible,
        )

        is_duplicate = (
            record.enrollment_no is not None and record.enrollment_no in seen_enrollment_nos
        ) or (record.seat_no is not None and record.seat_no in seen_seat_nos)
        if record.enrollment_no:
            seen_enrollment_nos.add(record.enrollment_no)
        if record.seat_no:
            seen_seat_nos.add(record.seat_no)

        matched = None
        if record.enrollment_no:
            matched = by_enrollment_no.get(record.enrollment_no)
        if matched is None and record.seat_no:
            matched = by_seat_no.get(record.seat_no)

        if is_duplicate:
            record.status = "duplicate_in_file"
            record.detail = "This enrollment/seat number appears more than once in the file"
        elif matched is None:
            record.status = "not_found"
            record.detail = "No existing student account matches this enrollment/seat number"
        else:
            record.matched_student_id = matched.id
            if programme_prefix and not (matched.seat_no or "").startswith(programme_prefix):
                record.status = "wrong_programme"
                record.detail = (
                    "This student does not belong to this course's programme or expected "
                    "batch year -- if they are repeating this course, add them as a backlog "
                    "student instead"
                )
            elif matched.id in already_enrolled_ids:
                record.status = "already_enrolled"
                record.detail = "Already enrolled in this course"
            elif eligible is not True:
                record.status = "ineligible"
                record.detail = (
                    "Marked not eligible in the file"
                    if eligible is False
                    else "Eligible column is missing or unrecognized"
                )
            else:
                record.status = "ready"

        records.append(record)

    def _count(status: str) -> int:
        return sum(1 for r in records if r.status == status)

    return EnrollImportPreview(
        total_detected=len(records),
        ready_count=_count("ready"),
        ineligible_count=_count("ineligible"),
        not_found_count=_count("not_found"),
        wrong_programme_count=_count("wrong_programme"),
        already_enrolled_count=_count("already_enrolled"),
        duplicate_count=_count("duplicate_in_file"),
        records=records,
        detected_columns=detected_columns,
        warnings=warnings,
    )
