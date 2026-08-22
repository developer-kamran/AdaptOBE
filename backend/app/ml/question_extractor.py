"""AI-assisted extraction of questions (and header metadata) from an
uploaded assessment paper (PDF/Word) via the Groq API -- the same generative
approach `clo_generator.py` already established for this codebase. A
regex/layout parser would be too brittle across the range of real exam-paper
formats (MCQ styles, fill-blank markers, numbering conventions); an LLM
given the raw extracted text handles that variance the same way
clo_generator handles free-form CLO wording. Per CLAUDE.md's "If AI/OCR is
required for scanned documents, follow the project's existing approach
rather than introducing unnecessary architecture" -- Groq generative calls
are that existing approach, not a new one.

Writes nothing and touches no DB -- purely text in, structured suggestion
out. The caller (assessment_paper_import_service.py) compares the suggested
header fields against the real assessment/course/instructor and turns
suggested questions into an editable, faculty-reviewed preview; nothing here
is ever saved automatically.
"""

import json
from dataclasses import dataclass, field

from app.core.config import settings
from app.services.exceptions import LLMGenerationError

#: Same model clo_generator.py uses -- picked from this account's live
#: `models.list()`, see that module's comment for why the name matters.
MODEL_NAME = "openai/gpt-oss-120b"

#: Keeps the prompt (and therefore cost/latency) bounded -- a multi-page exam
#: paper's actual question content is almost never past this many characters
#: of extracted text.
MAX_TEXT_CHARS = 16000

_ALLOWED_TYPES = {"question", "mcq", "fill_blank", "true_false"}

_client = None


def get_client():
    """Return the shared AsyncGroq client, constructing it on first use."""
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise LLMGenerationError(
                "GROQ_API_KEY is not configured -- set it in backend/.env to use "
                "assessment paper upload."
            )
        from groq import AsyncGroq

        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


@dataclass
class ExtractedQuestionSuggestion:
    question_type: str  # one of _ALLOWED_TYPES
    text: str
    marks: float | None = None
    options: list[dict] | None = None  # mcq only: [{"label": "A", "text": "..."}]
    correct_option: str | None = None  # mcq only, if an answer key was present
    answer: str | None = None  # fill_blank only, if an answer key was present
    correct_answer: bool | None = None  # true_false only, if an answer key was present
    clo_hint: str | None = None  # e.g. "CLO-7", if the paper marks one next to the question


@dataclass
class ExtractedPaperSuggestion:
    course_name: str | None
    course_code: str | None
    assessment_title: str | None
    instructor: str | None
    questions: list[ExtractedQuestionSuggestion] = field(default_factory=list)


def _build_prompt(document_text: str) -> str:
    return (
        "You are reading a university exam/assessment paper (a Quiz, Assignment, "
        "Midterm, or Final) and extracting its structure as JSON. The text below "
        "was mechanically extracted from the uploaded document and may have "
        "imperfect spacing or line breaks.\n\n"
        f"--- DOCUMENT TEXT START ---\n{document_text}\n--- DOCUMENT TEXT END ---\n\n"
        "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
        "{\n"
        '  "course_name": "the course title if printed on the paper, else null",\n'
        '  "course_code": "the course code if printed, else null",\n'
        '  "assessment_title": "the assessment/paper title if printed (e.g. '
        '\\"Quiz 1\\", \\"Assignment 2\\", \\"Midterm Exam\\"), else null",\n'
        '  "instructor": "the instructor/examiner name if printed, else null",\n'
        '  "questions": [\n'
        "    {\n"
        '      "question_type": "one of: question, mcq, fill_blank, true_false",\n'
        '      "text": "the question wording, without its number (for fill_blank, '
        'keep the blank as ___)",\n'
        '      "marks": marks as a plain number if printed near the question, else null,\n'
        '      "options": for mcq only, a list like [{"label": "A", "text": "..."}, '
        '{"label": "B", "text": "..."}], else null,\n'
        '      "correct_option": for mcq only, the option letter, ONLY if the document '
        "itself marks/states which is correct, else null,\n"
        '      "answer": for fill_blank only, the correct answer, ONLY if the document '
        "itself states it, else null,\n"
        '      "correct_answer": for true_false only, true or false, ONLY if the document '
        "itself states it, else null,\n"
        '      "clo_hint": the CLO code or label marked next to this question if the '
        'document tags one (e.g. "CLO-7", or "[CLO-7]", or a name like "Virtual Memory" '
        "if that's how it's marked instead of a code), else null\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "List every question found, in the order they appear on the paper. Most exam "
        "papers handed to students have no answer key -- leave correct_option/answer/"
        "correct_answer null whenever you cannot actually see the answer marked in the "
        "text, rather than guessing one. Likewise only fill in clo_hint when the "
        "document itself marks a CLO next to that question -- leave it null otherwise, "
        "never guess which CLO a question might belong to. If nothing on the page looks "
        'like a real question, return an empty "questions" list rather than inventing one.'
    )


def _coerce_marks(value) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_options(value) -> list[dict] | None:
    if not isinstance(value, list):
        return None
    options = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        text = str(item.get("text") or "").strip()
        if label:
            options.append({"label": label, "text": text})
    return options or None


def _text_or_none(value) -> str | None:
    text = str(value or "").strip()
    return text or None


def _coerce_bool_or_none(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "false"):
            return lowered == "true"
    return None


def _parse_response(raw: str) -> ExtractedPaperSuggestion:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise LLMGenerationError("The AI response was not valid JSON") from exc

    if not isinstance(data, dict):
        raise LLMGenerationError("The AI response was not a JSON object")

    raw_questions = data.get("questions")
    questions: list[ExtractedQuestionSuggestion] = []
    if isinstance(raw_questions, list):
        for item in raw_questions:
            if not isinstance(item, dict):
                continue
            text = _text_or_none(item.get("text"))
            if not text:
                continue
            question_type = str(item.get("question_type") or "question").strip()
            if question_type not in _ALLOWED_TYPES:
                question_type = "question"

            questions.append(
                ExtractedQuestionSuggestion(
                    question_type=question_type,
                    text=text,
                    marks=_coerce_marks(item.get("marks")),
                    options=_coerce_options(item.get("options")),
                    correct_option=_text_or_none(item.get("correct_option")),
                    answer=_text_or_none(item.get("answer")),
                    correct_answer=_coerce_bool_or_none(item.get("correct_answer")),
                    clo_hint=_text_or_none(item.get("clo_hint")),
                )
            )

    return ExtractedPaperSuggestion(
        course_name=_text_or_none(data.get("course_name")),
        course_code=_text_or_none(data.get("course_code")),
        assessment_title=_text_or_none(data.get("assessment_title")),
        instructor=_text_or_none(data.get("instructor")),
        questions=questions,
    )


async def aextract_paper(document_text: str) -> ExtractedPaperSuggestion:
    """Ask Groq to extract header metadata + questions from an assessment
    paper's raw text. Raises LLMGenerationError on any failure -- network,
    API, or malformed output -- so callers only need to handle one type."""
    client = get_client()
    prompt = _build_prompt(document_text[:MAX_TEXT_CHARS])

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_completion_tokens=4000,
        )
    except Exception as exc:  # noqa: BLE001 - any SDK/network failure becomes one typed error
        raise LLMGenerationError(f"AI question extraction request failed: {exc}") from exc

    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise LLMGenerationError("The AI returned an empty response")

    return _parse_response(content)
