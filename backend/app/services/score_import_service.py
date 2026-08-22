"""Score-sheet import: file -> preview -> confirmed scores.

Mirrors the preview/confirm split in `enrollment_import_service.py`: `build_preview`
touches no `student_scores` rows. `confirm` builds a `BulkScoreRequest` from the
already-matched, already-ready rows and delegates to the *existing*
`score_service.bulk_enter_scores` -- no parallel write path, so the same
all-or-nothing validation (marks_obtained <= question.marks, enrollment check)
applies at commit time too, as defense in depth even if a row slipped through
the preview as "ready".
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import column_matcher
from app.models.assessment import Assessment
from app.models.question import Question
from app.models.user import User
from app.schemas.score import ScoreEntry
from app.schemas.score_import import (
    DetectedQuestionColumn,
    ExtractedScoreRow,
    ScoreImportPreview,
)
from app.services import enrollment_service, file_parsers


def _value_at(row: list[str], index: int | None) -> str | None:
    if index is None or index >= len(row):
        return None
    value = row[index].strip()
    return value or None


def _parse_mark(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


async def build_preview(
    db: AsyncSession, assessment: Assessment, content: bytes, filename: str
) -> ScoreImportPreview:
    rows = file_parsers.parse_file(content, filename)
    warnings: list[str] = []

    questions = list(
        (
            await db.execute(
                select(Question)
                .where(Question.assessment_id == assessment.id)
                .order_by(Question.question_number)
            )
        )
        .scalars()
        .all()
    )

    if not rows:
        return ScoreImportPreview(
            total_detected=0,
            ready_count=0,
            student_not_found_count=0,
            duplicate_count=0,
            no_marks_count=0,
            records=[],
            detected_columns={"full_name": None, "seat_no": None},
            detected_question_columns=[
                DetectedQuestionColumn(
                    question_id=q.id, question_number=q.question_number, header=None, matched_by=None
                )
                for q in questions
            ],
            warnings=[
                "No table could be detected in this file. For PDFs, the sheet "
                "must be a real table rather than free text."
            ],
        )

    header_row, *data_rows = rows

    identity_detected = await column_matcher.match_columns(
        header_row, column_matcher.SCORE_IMPORT_FIELD_PROMPTS, column_matcher.SCORE_IMPORT_ALIASES
    )
    identity_columns = {i for i in identity_detected.values() if i is not None}

    question_matches = column_matcher.match_question_columns(header_row, questions, identity_columns)

    detected_columns = {
        field: (header_row[index] if index is not None and index < len(header_row) else None)
        for field, index in identity_detected.items()
    }
    detected_question_columns = [
        DetectedQuestionColumn(
            question_id=q.id,
            question_number=q.question_number,
            header=header_row[question_matches[q.id].index]
            if question_matches[q.id].index is not None
            else None,
            matched_by=question_matches[q.id].matched_by,
        )
        for q in questions
    ]

    if identity_detected.get("full_name") is None and identity_detected.get("seat_no") is None:
        warnings.append(
            "Neither a Full Name nor a Seat No. column could be found, so students "
            "cannot be matched."
        )
    unmatched_questions = [q for q in questions if question_matches[q.id].index is None]
    if unmatched_questions:
        numbers = ", ".join(f"Q{q.question_number}" for q in unmatched_questions)
        warnings.append(f"No column could be matched for: {numbers}")

    # Enrolled roster only -- a seat_no valid elsewhere isn't valid for this
    # assessment's course.
    student_ids = await enrollment_service.list_enrolled_student_ids(db, assessment.course_id)
    roster = list(
        (await db.execute(select(User).where(User.id.in_(student_ids or [0])))).scalars().all()
    )
    by_seat_no = {s.seat_no: s for s in roster if s.seat_no}
    by_full_name = {s.full_name.strip().lower(): s for s in roster if s.full_name}

    question_by_id = {q.id: q for q in questions}
    seen_identity: set[str] = set()
    records: list[ExtractedScoreRow] = []

    for offset, row in enumerate(data_rows, start=2):
        full_name = _value_at(row, identity_detected.get("full_name"))
        seat_no = _value_at(row, identity_detected.get("seat_no"))
        if not full_name and not seat_no:
            continue  # spacing/footer noise

        identity_key = seat_no or (full_name or "").strip().lower()
        is_duplicate = identity_key in seen_identity
        seen_identity.add(identity_key)

        matched = by_seat_no.get(seat_no) if seat_no else None
        if matched is None and full_name:
            matched = by_full_name.get(full_name.strip().lower())

        marks: dict[int, float] = {}
        rejected: dict[int, str] = {}
        for question in questions:
            column_index = question_matches[question.id].index
            raw = _value_at(row, column_index)
            if raw is None:
                continue
            value = _parse_mark(raw)
            if value is None:
                rejected[question.id] = f"{raw!r} is not a number"
            elif value < 0:
                rejected[question.id] = "Marks cannot be negative"
            elif value > question.marks:
                rejected[question.id] = f"Exceeds this question's {question.marks:g} marks"
            else:
                marks[question.id] = value

        if is_duplicate:
            status, detail = "duplicate_in_file", "This student appears more than once in the file"
        elif matched is None:
            status, detail = "student_not_found", "No enrolled student matches this name/seat number"
        elif not marks:
            status, detail = "no_marks", "No valid marks were found for this student"
        else:
            status, detail = "ready", ""

        records.append(
            ExtractedScoreRow(
                row_number=offset,
                full_name=full_name,
                seat_no=seat_no,
                matched_student_id=matched.id if matched else None,
                marks=marks,
                rejected_marks=rejected,
                status=status,
                detail=detail,
            )
        )

    def _count(status: str) -> int:
        return sum(1 for r in records if r.status == status)

    return ScoreImportPreview(
        total_detected=len(records),
        ready_count=_count("ready"),
        student_not_found_count=_count("student_not_found"),
        duplicate_count=_count("duplicate_in_file"),
        no_marks_count=_count("no_marks"),
        records=records,
        detected_columns=detected_columns,
        detected_question_columns=detected_question_columns,
        warnings=warnings,
    )


def scores_from_ready_records(records: list[ExtractedScoreRow]) -> list[ScoreEntry]:
    """Flatten ready rows' per-question marks into the shape `bulk_enter_scores`
    expects. Exposed separately so a test can exercise it without HTTP."""
    entries: list[ScoreEntry] = []
    for record in records:
        if record.status != "ready" or record.matched_student_id is None:
            continue
        for question_id, value in record.marks.items():
            entries.append(
                ScoreEntry(question_id=question_id, student_id=record.matched_student_id, marks_obtained=value)
            )
    return entries
