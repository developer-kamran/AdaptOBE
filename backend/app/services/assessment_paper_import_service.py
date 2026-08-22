"""Assessment-paper upload -> extraction preview, for the "Upload Assessment
Paper" feature: faculty upload the actual exam/quiz/assignment paper and get
back a reviewable list of extracted questions, instead of typing every
question by hand.

Follows the same upload -> preview -> confirm shape as every other import in
this codebase (score_import_service.py, enrollment_import_service.py), with
one simplification: there is no separate confirm/write endpoint here at all.
`build_preview` writes nothing, and the frontend's confirm step calls the
*existing* `POST /assessments/{id}/questions/bulk` endpoint directly with
whatever the faculty has reviewed/edited/deselected -- so there is no
parallel write path to keep in sync, and the same numbering/marks-budget/
CLO-ownership validation `question_service.bulk_create_questions` already
enforces applies here too, as-is.

Extraction itself (question_extractor.aextract_paper) is a generative LLM
call -- see that module's docstring for why that's this codebase's
"existing approach" for anything AI/OCR-shaped, not a new one.
"""

import difflib

from app.ml import question_extractor
from app.models.assessment import Assessment
from app.models.clo import CLO
from app.models.course import Course
from app.models.user import User
from app.schemas.assessment_paper_import import (
    AssessmentPaperPreview,
    AssessmentPaperVerification,
    DetectedField,
    ExtractedQuestionRow,
)
from app.services import file_parsers

#: Below this SequenceMatcher ratio (after normalizing whitespace/case), two
#: strings are treated as not matching -- unless one simply contains the
#: other, which is checked first and catches the common case of a course
#: name/title printed with extra words around it.
_FUZZY_MATCH_THRESHOLD = 0.6


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_code(value: str) -> str:
    """Course codes are compared ignoring punctuation/spacing entirely
    ("CS-301" vs "CS 301" vs "CS301" should all match) rather than via the
    fuzzy-ratio path, which is tuned for prose, not short codes."""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _matches(detected: str | None, expected: str, *, is_code: bool = False) -> bool:
    if not detected or not expected:
        return False
    if is_code:
        # Codes are short identifiers, not prose -- exact match only (after
        # stripping punctuation/case) rather than fuzzy/containment, which
        # would happily call "CS-201" a match for "CS-101" (one digit
        # apart is still a >60% character overlap) or "CS-10" a match for
        # "CS-101" (a plain prefix).
        d, e = _normalize_code(detected), _normalize_code(expected)
        return bool(d) and d == e

    d, e = _normalize(detected), _normalize(expected)
    if not d or not e:
        return False
    if d == e or d in e or e in d:
        return True
    return difflib.SequenceMatcher(None, d, e).ratio() >= _FUZZY_MATCH_THRESHOLD


def _field(detected: str | None, expected: str, *, is_code: bool = False) -> DetectedField:
    return DetectedField(
        detected=detected, expected=expected, matches=_matches(detected, expected, is_code=is_code)
    )


def match_clo(hint: str | None, clos: list[CLO]) -> int | None:
    """Resolve a document's CLO hint (e.g. "[CLO-7]", "CLO 7", or a topic
    name like "Virtual Memory") against this course's real CLOs. Only a
    *suggestion* -- the faculty can always change it (or use "Suggest with
    AI") in the confirmation preview, same as manual question entry;
    resolving it here just saves that step when the document already says
    so unambiguously. Code match first (exact, punctuation/case-insensitive,
    same discipline as course-code matching), title match as a fuzzy
    fallback for a hint that names the CLO instead of coding it. None if
    nothing lines up, rather than guessing."""
    if not hint:
        return None
    normalized_hint = _normalize_code(hint)
    for clo in clos:
        if _normalize_code(clo.code) == normalized_hint:
            return clo.id
    for clo in clos:
        if _matches(hint, clo.title):
            return clo.id
    return None


def _type_data_for(question: question_extractor.ExtractedQuestionSuggestion) -> dict | None:
    if question.question_type == "mcq":
        options = question.options or [{"label": label, "text": ""} for label in "ABCD"]
        correct_option = question.correct_option or options[0]["label"]
        return {"options": options, "correct_option": correct_option}
    if question.question_type == "fill_blank":
        return {"answer": question.answer or ""}
    if question.question_type == "true_false":
        correct = question.correct_answer if question.correct_answer is not None else True
        return {"correct_answer": correct}
    return None


def build_verification(
    suggestion: question_extractor.ExtractedPaperSuggestion,
    course: Course,
    assessment: Assessment,
    instructor: User | None,
) -> AssessmentPaperVerification:
    instructor_name = instructor.full_name if instructor else ""
    course_name = _field(suggestion.course_name, course.name)
    course_code = _field(suggestion.course_code, course.code, is_code=True)
    assessment_title = _field(suggestion.assessment_title, assessment.title)
    instructor_field = _field(suggestion.instructor, instructor_name)

    return AssessmentPaperVerification(
        course_name=course_name,
        course_code=course_code,
        assessment_title=assessment_title,
        instructor=instructor_field,
        all_matched=all(
            [
                course_name.matches,
                course_code.matches,
                assessment_title.matches,
                instructor_field.matches,
            ]
        ),
    )


async def build_preview(
    course: Course,
    assessment: Assessment,
    instructor: User | None,
    clos: list[CLO],
    content: bytes,
    filename: str,
) -> AssessmentPaperPreview:
    text = file_parsers.extract_document_text(content, filename)
    if not text.strip():
        raise file_parsers.FileParseError(
            "No readable text was found in this document. If it's a scanned "
            "image rather than a real document, it can't be extracted automatically."
        )

    suggestion = await question_extractor.aextract_paper(text)
    verification = build_verification(suggestion, course, assessment, instructor)

    questions = [
        ExtractedQuestionRow(
            question_number=index,
            question_type=q.question_type,
            text=q.text,
            marks=q.marks,
            type_data=_type_data_for(q),
            clo_id=match_clo(q.clo_hint, clos),
        )
        for index, q in enumerate(suggestion.questions, start=1)
    ]

    warnings: list[str] = []
    if not questions:
        warnings.append("No questions could be detected in this document.")
    if not verification.all_matched:
        warnings.append(
            "This document's details don't clearly match this assessment -- "
            "double-check before importing anything."
        )

    return AssessmentPaperPreview(verification=verification, questions=questions, warnings=warnings)
