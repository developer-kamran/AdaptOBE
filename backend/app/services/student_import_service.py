"""Bulk student import: file -> preview -> confirmed creation.

Two distinct phases, deliberately:
  * `build_preview` touches no database at all. Uploading a file can never
    create an account by itself.
  * `commit_students` creates accounts, and does so through the existing
    `user_service.create_user_scoped`, which already forces the caller's own
    `dept_id` and rejects any role but faculty/student. Department isolation
    therefore needs no new code here.
"""

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_password
from app.ml import column_matcher
from app.models.user import User, UserRole
from app.schemas.student_import import (
    FIELD_LABELS,
    REQUIRED_FIELDS,
    ConfirmStudent,
    ExtractedStudent,
    ImportedStudentResult,
    ImportPreview,
    ImportResult,
)
from app.schemas.user import UserCreate
from app.services import file_parsers, user_service
from app.services.exceptions import ConflictError, ValidationError

#: Good enough to catch "not an address at all" without rejecting valid but
#: unusual addresses. Authoritative validation happens at confirm time via
#: Pydantic's EmailStr.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _looks_like_header_row(row: list[str], detected: dict[str, int | None]) -> bool:
    """A detected header row shouldn't also be imported as a student."""
    return any(
        index is not None and row[index].strip().lower() in {"name", "full name", "email"}
        for index in detected.values()
        if index is not None and index < len(row)
    )


def _value_at(row: list[str], index: int | None) -> str | None:
    if index is None or index >= len(row):
        return None
    value = row[index].strip()
    return value or None


def _evaluate(
    record: ExtractedStudent,
    seen_emails: set[str],
    seen_enrollments: set[str],
    seen_seat_numbers: set[str],
) -> None:
    """Fill in `missing_fields`, `issues` and `is_complete` for one row."""
    for field in REQUIRED_FIELDS:
        if not getattr(record, field):
            record.missing_fields.append(FIELD_LABELS[field])

    if record.email and not _EMAIL_PATTERN.match(record.email):
        record.issues.append("Email address is not valid")
    elif record.email:
        lowered = record.email.lower()
        if lowered in seen_emails:
            record.issues.append("Duplicate email in this file")
        else:
            seen_emails.add(lowered)

    if record.enrollment_no:
        if record.enrollment_no in seen_enrollments:
            record.issues.append("Duplicate enrollment number in this file")
        else:
            seen_enrollments.add(record.enrollment_no)

    # Enrollment No and Seat No must each be unique, same as the DB-level
    # constraint on both columns -- this just surfaces an in-file clash at
    # preview time instead of leaving one of the two rows to be silently
    # skipped at confirm time.
    if record.seat_no:
        if record.seat_no in seen_seat_numbers:
            record.issues.append("Duplicate seat number in this file")
        else:
            seen_seat_numbers.add(record.seat_no)

    record.is_complete = not record.missing_fields and not record.issues


async def build_preview(content: bytes, filename: str) -> ImportPreview:
    """Parse and validate an uploaded roster. Reads nothing, writes nothing."""
    rows = file_parsers.parse_file(content, filename)
    warnings: list[str] = []

    if not rows:
        return ImportPreview(
            total_detected=0,
            complete_count=0,
            incomplete_count=0,
            records=[],
            detected_columns={field: None for field in REQUIRED_FIELDS},
            warnings=[
                "No table could be detected in this file. For PDFs, the roster "
                "must be a real table rather than free text."
            ],
        )

    header_row, *data_rows = rows
    detected = await column_matcher.match_columns(header_row)
    detected_columns = {
        field: (header_row[index] if index is not None and index < len(header_row) else None)
        for field, index in detected.items()
    }

    unmatched = [FIELD_LABELS[f] for f in REQUIRED_FIELDS if detected.get(f) is None]
    if unmatched:
        warnings.append(
            "These columns could not be found in the file, so every row will be "
            f"incomplete: {', '.join(unmatched)}"
        )

    records: list[ExtractedStudent] = []
    seen_emails: set[str] = set()
    seen_enrollments: set[str] = set()
    seen_seat_numbers: set[str] = set()

    for offset, row in enumerate(data_rows, start=2):  # row 1 is the header
        if _looks_like_header_row(row, detected):
            continue
        record = ExtractedStudent(
            row_number=offset,
            full_name=_value_at(row, detected.get("full_name")),
            father_name=_value_at(row, detected.get("father_name")),
            enrollment_no=_value_at(row, detected.get("enrollment_no")),
            seat_no=_value_at(row, detected.get("seat_no")),
            email=_value_at(row, detected.get("email")),
        )
        # A row where nothing at all was extracted is spacing/footer noise.
        if not any(getattr(record, field) for field in REQUIRED_FIELDS):
            continue
        _evaluate(record, seen_emails, seen_enrollments, seen_seat_numbers)
        records.append(record)

    complete_count = sum(1 for record in records if record.is_complete)
    return ImportPreview(
        total_detected=len(records),
        complete_count=complete_count,
        incomplete_count=len(records) - complete_count,
        records=records,
        detected_columns=detected_columns,
        warnings=warnings,
    )


async def commit_students(
    db: AsyncSession, students: list[ConfirmStudent], current_user: User
) -> ImportResult:
    """Create one account per confirmed row.

    Each student is created independently so a single clash (an email or
    enrollment number already taken) skips just that row instead of losing
    the whole batch -- `auth_service.register_user` already rolls back
    cleanly and raises ConflictError in that case.
    """
    if current_user.role != UserRole.sub_admin:
        # Belt-and-braces; the router guard enforces this too.
        raise ValidationError("Only sub-admins can import students")

    results: list[ImportedStudentResult] = []
    created_count = 0
    used_passwords: set[str] = set()

    for student in students:
        password = generate_password()
        while password in used_passwords:  # distinct password per student
            password = generate_password()
        used_passwords.add(password)

        data = UserCreate(
            email=student.email,
            password=password,
            full_name=student.full_name,
            role=UserRole.student,
            father_name=student.father_name,
            enrollment_no=student.enrollment_no,
            seat_no=student.seat_no,
        )

        try:
            # Forces dept_id to this sub-admin's own department.
            await user_service.create_user_scoped(db, data, current_user)
        except (ConflictError, ValidationError) as exc:
            results.append(
                ImportedStudentResult(
                    full_name=student.full_name,
                    email=student.email,
                    enrollment_no=student.enrollment_no,
                    status="skipped",
                    error=str(exc),
                )
            )
            continue

        created_count += 1
        results.append(
            ImportedStudentResult(
                full_name=student.full_name,
                email=student.email,
                enrollment_no=student.enrollment_no,
                generated_password=password,
                status="created",
            )
        )

    return ImportResult(
        created_count=created_count,
        skipped_count=len(results) - created_count,
        results=results,
    )
