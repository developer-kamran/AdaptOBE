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

_prompt_embeddings_cache: dict[int, dict[str, list[float]]] = {}


def normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """`embeddings.encode_text` returns unit vectors, so the dot product *is*
    the cosine similarity -- no division, no numpy needed."""
    return sum(x * y for x, y in zip(a, b))


def _encode_prompts(field_prompts: dict[str, str]) -> dict[str, list[float]]:
    """Encode a set of field prompts once per process; they never change.
    Cached per prompt-set (by its id) so both the student-import field set
    and the enrollment-import field set only get encoded once each."""
    cache_key = id(field_prompts)
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
