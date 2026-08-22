"""Match an uploaded roster's column headers to the student fields we need.

A roster written by a human says "Father's Name", "Guardian", "S/O", or
"Parent" for the same thing. Rather than maintaining an ever-growing list of
spellings, unrecognized headers are matched *semantically* with the same
`all-MiniLM-L6-v2` model the CLO-to-PLO mapping engine already uses.

Two-stage on purpose:
  1. A normalized alias lookup handles the overwhelmingly common case (a clean
     export with obvious headers) exactly, instantly, and deterministically.
  2. Anything left over falls back to embedding similarity, which is what
     makes unfamiliar wording work at all.
"""

import asyncio
import re

from app.ml import embeddings

#: Minimum cosine similarity before we'll believe a semantic match. Tuned to
#: accept "Guardian Name" -> father_name while rejecting unrelated columns
#: like "Section" or "CGPA".
SIMILARITY_THRESHOLD = 0.45

#: Canonical field -> descriptive phrase fed to the encoder. These read like
#: natural language rather than identifiers because that is what the sentence
#: model was trained on.
FIELD_PROMPTS: dict[str, str] = {
    "full_name": "full name of the student",
    "father_name": "father name, guardian name, parent name",
    "enrollment_no": "enrollment number, registration number",
    "seat_no": "seat number, roll number, examination number",
    "email": "email address",
}

#: Exact matches after normalization (lowercased, non-alphanumerics stripped).
#: Only unambiguous spellings belong here -- anything debatable should go
#: through the embedding path instead.
_ALIASES: dict[str, str] = {
    "name": "full_name",
    "fullname": "full_name",
    "studentname": "full_name",
    "student": "full_name",
    "fathername": "father_name",
    "fathersname": "father_name",
    "guardianname": "father_name",
    "parentname": "father_name",
    "enrollmentno": "enrollment_no",
    "enrollmentnumber": "enrollment_no",
    "enrolmentno": "enrollment_no",
    "enrollment": "enrollment_no",
    "regno": "enrollment_no",
    "registrationno": "enrollment_no",
    "seatno": "seat_no",
    "seatnumber": "seat_no",
    "rollno": "seat_no",
    "rollnumber": "seat_no",
    "email": "email",
    "emailaddress": "email",
    "emailid": "email",
}

#: Field prompts/aliases for the course-enrollment roster import, which asks
#: for "Eligible" instead of "Email" -- see `enrollment_import_service.py`.
ENROLLMENT_FIELD_PROMPTS: dict[str, str] = {
    "full_name": FIELD_PROMPTS["full_name"],
    "father_name": FIELD_PROMPTS["father_name"],
    "enrollment_no": FIELD_PROMPTS["enrollment_no"],
    "seat_no": FIELD_PROMPTS["seat_no"],
    "eligible": "eligible for enrollment, yes or no",
}

ENROLLMENT_ALIASES: dict[str, str] = {
    **{k: v for k, v in _ALIASES.items() if v != "email"},
    "eligible": "eligible",
    "iseligible": "eligible",
    "eligibility": "eligible",
    "status": "eligible",
}

#: Field prompts/aliases for the attendance-sheet import, which asks for
#: "Attendance %" instead of "Email" -- see `attendance_import_service.py`.
ATTENDANCE_FIELD_PROMPTS: dict[str, str] = {
    "full_name": FIELD_PROMPTS["full_name"],
    "father_name": FIELD_PROMPTS["father_name"],
    "seat_no": FIELD_PROMPTS["seat_no"],
    "attendance_percentage": "attendance percentage, attendance %, percent present",
}

ATTENDANCE_ALIASES: dict[str, str] = {
    **{k: v for k, v in _ALIASES.items() if v in ATTENDANCE_FIELD_PROMPTS},
    "attendance": "attendance_percentage",
    "attendancepercent": "attendance_percentage",
    "attendancepercentage": "attendance_percentage",
    "attendancepct": "attendance_percentage",
    "percentattendance": "attendance_percentage",
}

#: Identity-field prompts/aliases for the score-sheet import -- only name/seat
#: no are needed there (question-mark columns are matched separately by
#: `match_question_columns`, not through this embedding path -- see its
#: docstring for why). Derived from the same base sets as `ENROLLMENT_*` above.
SCORE_IMPORT_FIELD_PROMPTS: dict[str, str] = {
    "full_name": FIELD_PROMPTS["full_name"],
    "seat_no": FIELD_PROMPTS["seat_no"],
}

SCORE_IMPORT_ALIASES: dict[str, str] = {
    k: v for k, v in _ALIASES.items() if v in SCORE_IMPORT_FIELD_PROMPTS
}

_prompt_embeddings_cache: dict[tuple, dict[str, list[float]]] = {}


def normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """`embeddings.encode_text` returns unit vectors, so the dot product *is*
    the cosine similarity -- no division, no numpy needed."""
    return sum(x * y for x, y in zip(a, b))


def _encode_prompts(field_prompts: dict[str, str]) -> dict[str, list[float]]:
    """Encode a set of field prompts once per process; they never change for a
    given content. Cached by *content*, not `id(field_prompts)` -- a dict's id
    can be reused by Python after garbage collection, which would silently
    serve a stale/wrong cached embedding for a short-lived dict built fresh
    per request (as the score-import column matching does)."""
    cache_key = tuple(sorted(field_prompts.items()))
    if cache_key not in _prompt_embeddings_cache:
        _prompt_embeddings_cache[cache_key] = {
            field: embeddings.encode_text(prompt) for field, prompt in field_prompts.items()
        }
    return _prompt_embeddings_cache[cache_key]


def _match_columns_sync(
    headers: list[str],
    field_prompts: dict[str, str],
    aliases: dict[str, str],
) -> dict[str, int | None]:
    """Returns canonical field -> index of the column that supplies it."""
    assigned: dict[str, int] = {}
    unresolved: list[int] = []

    # Stage 1: exact alias match.
    for index, header in enumerate(headers):
        field = aliases.get(normalize_header(header))
        if field is not None and field not in assigned:
            assigned[field] = index
        elif header.strip():
            unresolved.append(index)

    # Stage 2: semantic match for whatever is left, best pairs first so a
    # single column can't be claimed by two fields (or vice versa).
    remaining_fields = [field for field in field_prompts if field not in assigned]
    if remaining_fields and unresolved:
        prompts = _encode_prompts(field_prompts)
        scored: list[tuple[float, str, int]] = []
        for index in unresolved:
            header_vector = embeddings.encode_text(headers[index])
            for field in remaining_fields:
                score = cosine_similarity(header_vector, prompts[field])
                if score >= SIMILARITY_THRESHOLD:
                    scored.append((score, field, index))

        scored.sort(key=lambda item: item[0], reverse=True)
        taken_columns: set[int] = set(assigned.values())
        for _score, field, index in scored:
            if field in assigned or index in taken_columns:
                continue
            assigned[field] = index
            taken_columns.add(index)

    return {field: assigned.get(field) for field in field_prompts}


def _question_number_aliases(question_number: int) -> set[str]:
    n = str(question_number)
    return {f"q{n}", f"question{n}", f"que{n}", f"marksq{n}", f"q{n}marks", f"qno{n}", f"qn{n}"}


class MatchedColumn:
    """One question's resolved scoresheet column, plus how it was resolved --
    `matched_by="position"` matches are shown to faculty for visual double-
    checking before they confirm, since a positional guess is weaker evidence
    than an explicit "Q3"-style header."""

    __slots__ = ("index", "matched_by")

    def __init__(self, index: int | None, matched_by: str | None):
        self.index = index
        self.matched_by = matched_by


def match_question_columns(
    headers: list[str], questions: list, excluded_columns: set[int] = frozenset()
) -> dict[int, MatchedColumn]:
    """Match a scoresheet's mark columns to specific questions.

    Deliberately does NOT use the embedding-similarity fallback `match_columns`
    relies on: "question 3" and "question 4" differ only by a number token
    surrounded by otherwise-identical words, so MiniLM cosine similarity
    between them is unreliable noise, unlike genuinely distinct field names
    ("full name" vs "seat number"). Two stages instead:
      1. Alias match: normalized header against generated aliases per question
         number ("q1", "question1", "marksq1", ...).
      2. Positional fallback: whatever's left is assigned left-to-right by
         ascending question number, but only when the count of leftover
         columns equals the count of leftover questions -- exam mark sheets
         are almost always laid out in question order, but this only fires
         when that count match makes the guess unambiguous.

    `excluded_columns` should be the column indices already claimed by
    identity fields (name/seat_no/etc, matched separately via `match_columns`)
    so they're never miscounted as leftover question columns.
    """
    sorted_questions = sorted(questions, key=lambda q: q.question_number)
    assigned: dict[int, MatchedColumn] = {}
    used_columns: set[int] = set(excluded_columns)

    for question in sorted_questions:
        aliases = _question_number_aliases(question.question_number)
        for index, header in enumerate(headers):
            if index in used_columns:
                continue
            if normalize_header(header) in aliases:
                assigned[question.id] = MatchedColumn(index, "alias")
                used_columns.add(index)
                break

    unmatched_questions = [q for q in sorted_questions if q.id not in assigned]
    unmatched_columns = [
        i for i, header in enumerate(headers) if i not in used_columns and header.strip()
    ]
    if unmatched_questions and len(unmatched_questions) == len(unmatched_columns):
        for question, index in zip(unmatched_questions, unmatched_columns):
            assigned[question.id] = MatchedColumn(index, "position")

    return {
        question.id: assigned.get(question.id, MatchedColumn(None, None))
        for question in questions
    }


async def match_columns(
    headers: list[str],
    field_prompts: dict[str, str] | None = None,
    aliases: dict[str, str] | None = None,
) -> dict[str, int | None]:
    """Async wrapper -- encoding is CPU-bound, so it must not run on the
    event loop (same reason `embeddings.aencode_text` exists).

    Defaults to the student-import field set (full_name/father_name/
    enrollment_no/seat_no/email) for backward compatibility; pass
    `ENROLLMENT_FIELD_PROMPTS`/`ENROLLMENT_ALIASES` for the course-enrollment
    roster import instead."""
    return await asyncio.to_thread(
        _match_columns_sync,
        headers,
        field_prompts if field_prompts is not None else FIELD_PROMPTS,
        aliases if aliases is not None else _ALIASES,
    )
