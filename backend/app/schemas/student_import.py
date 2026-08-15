from pydantic import BaseModel, EmailStr, Field

#: Every field a student account needs. Order matters -- it drives the
#: preview table's column order in the UI.
REQUIRED_FIELDS: tuple[str, ...] = (
    "full_name",
    "father_name",
    "enrollment_no",
    "seat_no",
    "email",
)

#: Human-readable labels for the messages the UI shows ("Missing: Father's Name").
FIELD_LABELS: dict[str, str] = {
    "full_name": "Full Name",
    "father_name": "Father's Name",
    "enrollment_no": "Enrollment No",
    "seat_no": "Seat No",
    "email": "Email",
}


class ExtractedStudent(BaseModel):
    """One row as read out of the uploaded file. Every field is optional here
    on purpose: this represents what the file *said*, not a valid student.
    `email` is a plain str rather than EmailStr for the same reason -- an
    unparseable address must survive extraction so it can be reported."""

    row_number: int
    full_name: str | None = None
    father_name: str | None = None
    enrollment_no: str | None = None
    seat_no: str | None = None
    email: str | None = None
    #: Required fields that were blank or absent.
    missing_fields: list[str] = Field(default_factory=list)
    #: Everything else wrong with the row (malformed email, duplicated within
    #: the same file). Kept separate so the UI can phrase them differently.
    issues: list[str] = Field(default_factory=list)
    is_complete: bool = False


class ImportPreview(BaseModel):
    total_detected: int
    complete_count: int
    incomplete_count: int
    records: list[ExtractedStudent]
    #: Canonical field -> the header text it was matched to (or None). Shown
    #: in the UI so the extraction isn't a black box.
    detected_columns: dict[str, str | None]
    warnings: list[str] = Field(default_factory=list)


class ConfirmStudent(BaseModel):
    """A row the user confirmed. Re-validated server-side: the browser
    deciding a row is complete is not something to take on trust."""

    full_name: str = Field(min_length=1, max_length=255)
    father_name: str = Field(min_length=1, max_length=255)
    enrollment_no: str = Field(min_length=1, max_length=50)
    seat_no: str = Field(min_length=1, max_length=50)
    email: EmailStr


class ConfirmImportRequest(BaseModel):
    students: list[ConfirmStudent] = Field(min_length=1)


class ImportedStudentResult(BaseModel):
    full_name: str
    email: str
    enrollment_no: str
    #: Only populated when status == "created".
    generated_password: str | None = None
    status: str  # "created" | "skipped"
    error: str | None = None


class ImportResult(BaseModel):
    created_count: int
    skipped_count: int
    results: list[ImportedStudentResult]
