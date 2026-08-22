"""Assessment-paper upload -> extraction preview.

Two layers, same split as test_score_import.py: pure matching-logic tests
against `assessment_paper_import_service` directly (no DB, no HTTP), plus
API-level tests that monkeypatch `question_extractor.aextract_paper` so the
router path is exercised without a real Groq call.
"""

from io import BytesIO

import pytest
from docx import Document

from app.ml import question_extractor
from app.services import assessment_paper_import_service as svc
from tests.conftest import auth_header


# ---------------------------------------------------------------------------
# Pure matching logic
# ---------------------------------------------------------------------------


def test_matches_exact():
    assert svc._matches("Introduction to Programming", "Introduction to Programming")


def test_matches_case_and_whitespace_insensitive():
    assert svc._matches("  introduction   TO Programming ", "Introduction to Programming")


def test_matches_containment():
    assert svc._matches("CS-101 -- Introduction to Programming (Quiz 1)", "Introduction to Programming")


def test_matches_none_detected_is_not_a_match():
    assert not svc._matches(None, "Introduction to Programming")


def test_matches_totally_different_text_fails():
    assert not svc._matches("Database Systems", "Introduction to Programming")


def test_code_match_ignores_punctuation_and_case():
    assert svc._matches("cs 101", "CS-101", is_code=True)
    assert svc._matches("CS101", "CS-101", is_code=True)


def test_code_match_different_codes_fail():
    assert not svc._matches("CS-201", "CS-101", is_code=True)


def test_type_data_for_mcq_defaults_options_and_correct_option():
    q = question_extractor.ExtractedQuestionSuggestion(question_type="mcq", text="Q")
    data = svc._type_data_for(q)
    assert len(data["options"]) == 4
    assert data["correct_option"] == "A"


def test_type_data_for_mcq_uses_extracted_values():
    q = question_extractor.ExtractedQuestionSuggestion(
        question_type="mcq",
        text="Q",
        options=[{"label": "A", "text": "x"}, {"label": "B", "text": "y"}],
        correct_option="B",
    )
    data = svc._type_data_for(q)
    assert data["options"] == [{"label": "A", "text": "x"}, {"label": "B", "text": "y"}]
    assert data["correct_option"] == "B"


def test_type_data_for_true_false_defaults_to_true_when_unknown():
    q = question_extractor.ExtractedQuestionSuggestion(question_type="true_false", text="Q")
    assert svc._type_data_for(q) == {"correct_answer": True}


def test_type_data_for_fill_blank_defaults_empty_answer():
    q = question_extractor.ExtractedQuestionSuggestion(question_type="fill_blank", text="Q")
    assert svc._type_data_for(q) == {"answer": ""}


def test_type_data_for_plain_question_is_none():
    q = question_extractor.ExtractedQuestionSuggestion(question_type="question", text="Q")
    assert svc._type_data_for(q) is None


class _FakeCLO:
    def __init__(self, id, code, title):
        self.id = id
        self.code = code
        self.title = title


def test_match_clo_by_code_ignoring_punctuation_and_case():
    clos = [_FakeCLO(1, "CLO-7", "Virtual Memory"), _FakeCLO(2, "CLO-8", "File Systems")]
    assert svc.match_clo("[CLO-7]", clos) == 1
    assert svc.match_clo("clo 8", clos) == 2


def test_match_clo_falls_back_to_title_match():
    clos = [_FakeCLO(1, "CLO-7", "Virtual Memory"), _FakeCLO(2, "CLO-8", "File Systems")]
    assert svc.match_clo("Virtual Memory", clos) == 1


def test_match_clo_none_when_no_hint_or_no_match():
    clos = [_FakeCLO(1, "CLO-7", "Virtual Memory")]
    assert svc.match_clo(None, clos) is None
    assert svc.match_clo("CLO-99", clos) is None


# ---------------------------------------------------------------------------
# API-level: router + full build_preview, question_extractor monkeypatched
# ---------------------------------------------------------------------------


def build_docx(lines: list[str]) -> bytes:
    document = Document()
    for line in lines:
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def upload(content: bytes, filename: str = "paper.docx"):
    return {
        "file": (
            filename,
            content,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }


@pytest.fixture
def fake_extraction(monkeypatch):
    """Monkeypatch the Groq call with a canned suggestion. `course` and
    `faculty` fixtures fix the expected values: course.name = "Introduction
    to Programming", course.code = "CS-101", faculty.full_name = "Test User"."""

    def _install(suggestion: question_extractor.ExtractedPaperSuggestion):
        async def _fake(text):
            return suggestion

        monkeypatch.setattr(question_extractor, "aextract_paper", _fake)

    return _install


def matching_suggestion(assessment_title: str) -> question_extractor.ExtractedPaperSuggestion:
    return question_extractor.ExtractedPaperSuggestion(
        course_name="Introduction to Programming",
        course_code="CS-101",
        assessment_title=assessment_title,
        instructor="Test User",
        questions=[
            question_extractor.ExtractedQuestionSuggestion(
                question_type="question", text="Explain recursion.", marks=5
            ),
            question_extractor.ExtractedQuestionSuggestion(
                question_type="mcq",
                text="Which is a loop keyword?",
                marks=2,
                options=[{"label": "A", "text": "if"}, {"label": "B", "text": "while"}],
                correct_option="B",
            ),
        ],
    )


async def test_preview_all_matched_when_paper_matches_assessment(
    client, faculty, make_assessment, fake_extraction
):
    assessment = await make_assessment(title="Quiz 1", total_marks=10.0)
    fake_extraction(matching_suggestion("Quiz 1"))

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/paper-import/preview",
        files=upload(build_docx(["Quiz 1"])),
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verification"]["all_matched"] is True
    assert body["verification"]["course_name"]["matches"] is True
    assert len(body["questions"]) == 2
    assert body["questions"][0]["question_type"] == "question"
    assert body["questions"][1]["question_type"] == "mcq"
    assert body["questions"][1]["type_data"]["correct_option"] == "B"
    assert body["warnings"] == []


async def test_preview_resolves_clo_hint_to_real_clo_id(
    client, faculty, make_assessment, make_clo, fake_extraction
):
    assessment = await make_assessment(title="Quiz 1", total_marks=10.0)
    clo = await make_clo("CLO-7", "Virtual Memory", "Understand virtual memory concepts.")
    suggestion = matching_suggestion("Quiz 1")
    suggestion.questions[0].clo_hint = "[CLO-7]"  # matches the real CLO's code
    suggestion.questions[1].clo_hint = "CLO-99"  # no such CLO in this course
    fake_extraction(suggestion)

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/paper-import/preview",
        files=upload(build_docx(["Quiz 1"])),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["questions"][0]["clo_id"] == clo.id
    assert body["questions"][1]["clo_id"] is None


async def test_preview_flags_mismatched_assessment_title(client, faculty, make_assessment, fake_extraction):
    assessment = await make_assessment(title="Midterm Exam", total_marks=10.0)
    # Extracted paper says "Quiz 1" -- wrong document for this assessment.
    fake_extraction(matching_suggestion("Quiz 1"))

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/paper-import/preview",
        files=upload(build_docx(["Quiz 1"])),
        headers=auth_header(faculty),
    )
    body = resp.json()
    assert body["verification"]["all_matched"] is False
    assert body["verification"]["assessment_title"]["matches"] is False
    assert body["verification"]["assessment_title"]["detected"] == "Quiz 1"
    assert body["verification"]["assessment_title"]["expected"] == "Midterm Exam"
    assert any("match" in w.lower() for w in body["warnings"])


async def test_preview_no_questions_detected_is_warned_not_errored(
    client, faculty, make_assessment, fake_extraction
):
    assessment = await make_assessment(title="Quiz 1", total_marks=10.0)
    empty = question_extractor.ExtractedPaperSuggestion(
        course_name=None, course_code=None, assessment_title=None, instructor=None, questions=[]
    )
    fake_extraction(empty)

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/paper-import/preview",
        files=upload(build_docx(["some unrelated text"])),
        headers=auth_header(faculty),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["questions"] == []
    assert any("no questions" in w.lower() for w in body["warnings"])


async def test_preview_rejects_unsupported_file_type(client, faculty, make_assessment):
    assessment = await make_assessment(title="Quiz 1", total_marks=10.0)
    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/paper-import/preview",
        files={"file": ("paper.txt", b"hello", "text/plain")},
        headers=auth_header(faculty),
    )
    assert resp.status_code == 422


async def test_preview_requires_faculty_owner(client, make_user, make_assessment, fake_extraction):
    other = await make_user("faculty.paperimp@adaptobe.edu", role="faculty", employee_id="FAC-PAPERIMP")
    assessment = await make_assessment(title="Quiz 1", total_marks=10.0)
    fake_extraction(matching_suggestion("Quiz 1"))

    resp = await client.post(
        f"/api/v1/assessments/{assessment.id}/paper-import/preview",
        files=upload(build_docx(["Quiz 1"])),
        headers=auth_header(other),
    )
    assert resp.status_code == 403


async def test_preview_writes_no_questions(
    client, db_session, faculty, make_assessment, fake_extraction
):
    from sqlalchemy import select

    from app.models.question import Question

    assessment = await make_assessment(title="Quiz 1", total_marks=10.0)
    fake_extraction(matching_suggestion("Quiz 1"))

    await client.post(
        f"/api/v1/assessments/{assessment.id}/paper-import/preview",
        files=upload(build_docx(["Quiz 1"])),
        headers=auth_header(faculty),
    )

    questions = (
        await db_session.execute(select(Question).where(Question.assessment_id == assessment.id))
    ).scalars().all()
    assert questions == []
