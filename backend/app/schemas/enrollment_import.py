"""Course-enrollment roster import: file -> preview -> confirmed enrollment.

Deliberately distinct from `student_import.py`. That flow *creates accounts*
(sub-admin only, department-wide). This flow *enrolls existing accounts* into
one course (faculty only, scoped to that course's own programme) -- a row
that doesn't match an existing student is reported, never used to create one.
"""

from typing import Literal

from pydantic import BaseModel, Field

#: Every field the enrollment roster needs. Order drives the preview table's
#: column order in the UI, same convention as `student_import.py`.
REQUIRED_FIELDS: tuple[str, ...] = (
    "full_name",
    "father_name",
    "enrollment_no",
    "seat_no",
    "eligible",
)

FIELD_LABELS: dict[str, str] = {
    "full_name": "Full Name",
    "father_name": "Father's Name",
    "enrollment_no": "Enrollment No",
    "seat_no": "Seat No",
    "eligible": "Eligible",
}

RowStatus = Literal[
    "ready",
    "ineligible",
    "not_found",
    "wrong_programme",
    "already_enrolled",
    "duplicate_in_file",
]


class ExtractedEnrollmentRow(BaseModel):
    """One row as read out of the uploaded file, plus the outcome of trying
    to match and classify it. Nothing is enrolled at this stage."""

    row_number: int
    full_name: str | None = None
    father_name: str | None = None
    enrollment_no: str | None = None
    seat_no: str | None = None
    eligible: bool | None = None
    #: The existing student account this row matched, if any. Only rows with
    #: status "ready" are eligible to be confirmed.
    matched_student_id: int | None = None
    status: RowStatus = "not_found"
    detail: str = ""


class EnrollImportPreview(BaseModel):
    total_detected: int
    ready_count: int
    ineligible_count: int
    not_found_count: int
    wrong_programme_count: int
    already_enrolled_count: int
    duplicate_count: int
    records: list[ExtractedEnrollmentRow]
    detected_columns: dict[str, str | None]
    warnings: list[str] = Field(default_factory=list)


class ConfirmEnrollImportRequest(BaseModel):
    student_ids: list[int] = Field(min_length=1)
