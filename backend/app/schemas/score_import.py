from typing import Literal

from pydantic import BaseModel

from app.schemas.score import ScoreEntry

RowStatus = Literal["ready", "student_not_found", "duplicate_in_file", "no_marks"]


class ExtractedScoreRow(BaseModel):
    row_number: int
    full_name: str | None
    seat_no: str | None
    matched_student_id: int | None
    marks: dict[int, float]  # question_id -> marks_obtained, only valid (<= question.marks) cells
    rejected_marks: dict[int, str]  # question_id -> rejection reason, always shown, never dropped
    status: RowStatus
    detail: str = ""


class DetectedQuestionColumn(BaseModel):
    question_id: int
    question_number: int
    header: str | None
    matched_by: Literal["alias", "position"] | None


class ScoreImportPreview(BaseModel):
    total_detected: int
    ready_count: int
    student_not_found_count: int
    duplicate_count: int
    no_marks_count: int
    records: list[ExtractedScoreRow]
    detected_columns: dict[str, str | None]
    detected_question_columns: list[DetectedQuestionColumn]
    warnings: list[str] = []


class ConfirmScoreImportRequest(BaseModel):
    scores: list[ScoreEntry]
