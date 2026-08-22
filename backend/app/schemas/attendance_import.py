from typing import Literal

from pydantic import BaseModel

from app.schemas.attendance import AttendanceEntry

FIELD_LABELS: dict[str, str] = {
    "full_name": "Full Name",
    "father_name": "Father's Name",
    "seat_no": "Seat No",
    "attendance_percentage": "Attendance %",
}
REQUIRED_FIELDS = list(FIELD_LABELS.keys())

RowStatus = Literal["ready", "student_not_found", "duplicate_in_file", "invalid_percentage"]


class ExtractedAttendanceRow(BaseModel):
    row_number: int
    full_name: str | None = None
    father_name: str | None = None
    seat_no: str | None = None
    attendance_percentage_raw: str | None = None
    #: The enrolled student this row matched, if any. Only "ready" rows are
    #: eligible to be confirmed.
    matched_student_id: int | None = None
    status: RowStatus = "student_not_found"
    detail: str = ""


class AttendanceImportPreview(BaseModel):
    total_detected: int
    ready_count: int
    student_not_found_count: int
    duplicate_count: int
    invalid_percentage_count: int
    records: list[ExtractedAttendanceRow]
    detected_columns: dict[str, str | None]
    warnings: list[str] = []


class ConfirmAttendanceImportRequest(BaseModel):
    entries: list[AttendanceEntry]
