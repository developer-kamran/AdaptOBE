"""Pure/monkeypatched tests for app/ml/question_extractor.py -- never touches
the real Groq API or network, matching this repo's `stub_encoder` discipline
for the embedding model and test_clo_generator.py's discipline for the
other Groq-backed feature."""

import pytest

from app.core.config import settings
from app.ml import question_extractor
from app.services.exceptions import LLMGenerationError


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)] if content is not None else []


class _FakeCompletions:
    def __init__(self, content=None, error=None):
        self._content = content
        self._error = error

    async def create(self, **kwargs):
        if self._error:
            raise self._error
        return _FakeCompletion(self._content)


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, content=None, error=None):
        self.chat = _FakeChat(_FakeCompletions(content=content, error=error))


def test_parse_response_valid_full_shape():
    raw = """
    {
      "course_name": "Introduction to Programming",
      "course_code": "CS-101",
      "assessment_title": "Quiz 1",
      "instructor": "Dr. Ada Lovelace",
      "questions": [
        {"question_type": "question", "text": "Explain recursion.", "marks": 5},
        {"question_type": "mcq", "text": "Which is a loop?", "marks": 2,
         "options": [{"label": "A", "text": "if"}, {"label": "B", "text": "while"}],
         "correct_option": "B"},
        {"question_type": "true_false", "text": "Python is compiled.", "correct_answer": false},
        {"question_type": "fill_blank", "text": "A ___ stores a value.", "answer": "variable"}
      ]
    }
    """
    suggestion = question_extractor._parse_response(raw)
    assert suggestion.course_name == "Introduction to Programming"
    assert suggestion.course_code == "CS-101"
    assert suggestion.assessment_title == "Quiz 1"
    assert suggestion.instructor == "Dr. Ada Lovelace"
    assert len(suggestion.questions) == 4
    assert suggestion.questions[0].question_type == "question"
    assert suggestion.questions[1].correct_option == "B"
    assert suggestion.questions[2].correct_answer is False
    assert suggestion.questions[3].answer == "variable"


def test_parse_response_parses_clo_hint():
    raw = '{"questions": [{"question_type": "question", "text": "Explain paging.", "clo_hint": "[CLO-7]"}]}'
    suggestion = question_extractor._parse_response(raw)
    assert suggestion.questions[0].clo_hint == "[CLO-7]"


def test_parse_response_missing_clo_hint_is_none():
    raw = '{"questions": [{"question_type": "question", "text": "Explain paging."}]}'
    suggestion = question_extractor._parse_response(raw)
    assert suggestion.questions[0].clo_hint is None


def test_parse_response_missing_header_fields_are_none():
    suggestion = question_extractor._parse_response('{"questions": []}')
    assert suggestion.course_name is None
    assert suggestion.course_code is None
    assert suggestion.assessment_title is None
    assert suggestion.instructor is None
    assert suggestion.questions == []


def test_parse_response_unrecognized_question_type_falls_back_to_question():
    raw = '{"questions": [{"question_type": "essay", "text": "Write an essay."}]}'
    suggestion = question_extractor._parse_response(raw)
    assert suggestion.questions[0].question_type == "question"


def test_parse_response_skips_items_with_no_text():
    raw = '{"questions": [{"question_type": "question", "text": ""}, {"question_type": "question", "text": "Real one"}]}'
    suggestion = question_extractor._parse_response(raw)
    assert len(suggestion.questions) == 1
    assert suggestion.questions[0].text == "Real one"


def test_parse_response_malformed_json():
    with pytest.raises(LLMGenerationError):
        question_extractor._parse_response("not json at all")


def test_parse_response_not_an_object():
    with pytest.raises(LLMGenerationError):
        question_extractor._parse_response("[1, 2, 3]")


def test_coerce_marks_handles_bad_values():
    assert question_extractor._coerce_marks("5") == 5.0
    assert question_extractor._coerce_marks(None) is None
    assert question_extractor._coerce_marks("not a number") is None
    assert question_extractor._coerce_marks(True) is None


def test_coerce_options_drops_labelless_entries():
    options = question_extractor._coerce_options(
        [{"label": "A", "text": "x"}, {"label": "", "text": "dropped"}, "not a dict"]
    )
    assert options == [{"label": "A", "text": "x"}]


def test_get_client_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    question_extractor._client = None
    with pytest.raises(LLMGenerationError):
        question_extractor.get_client()


async def test_aextract_paper_success(monkeypatch):
    fake = _FakeClient(content='{"questions": [{"question_type": "question", "text": "Q1"}]}')
    monkeypatch.setattr(question_extractor, "get_client", lambda: fake)

    result = await question_extractor.aextract_paper("some exam paper text")
    assert len(result.questions) == 1
    assert result.questions[0].text == "Q1"


async def test_aextract_paper_wraps_client_errors(monkeypatch):
    fake = _FakeClient(error=RuntimeError("network down"))
    monkeypatch.setattr(question_extractor, "get_client", lambda: fake)

    with pytest.raises(LLMGenerationError):
        await question_extractor.aextract_paper("text")


async def test_aextract_paper_empty_response(monkeypatch):
    fake = _FakeClient(content=None)
    monkeypatch.setattr(question_extractor, "get_client", lambda: fake)

    with pytest.raises(LLMGenerationError):
        await question_extractor.aextract_paper("text")
