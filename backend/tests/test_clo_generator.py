"""Pure/monkeypatched tests for app/ml/clo_generator.py -- never touches the
real Groq API or network, matching this repo's `stub_encoder` discipline for
the embedding model."""

import pytest

from app.core.config import settings
from app.ml import clo_generator
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


def test_parse_response_valid():
    suggestion = clo_generator._parse_response(
        '{"title": "Apply Loops", "description": "Write programs using loops.", "bloom_level": "Apply"}'
    )
    assert suggestion.title == "Apply Loops"
    assert suggestion.bloom_level == "Apply"


def test_parse_response_malformed_json():
    with pytest.raises(LLMGenerationError):
        clo_generator._parse_response("not json at all")


def test_parse_response_missing_fields():
    with pytest.raises(LLMGenerationError):
        clo_generator._parse_response('{"title": "", "description": "", "bloom_level": "Apply"}')


def test_parse_response_bad_bloom_level():
    with pytest.raises(LLMGenerationError):
        clo_generator._parse_response(
            '{"title": "X", "description": "Y", "bloom_level": "NotARealLevel"}'
        )


def test_build_prompt_includes_inputs():
    prompt = clo_generator._build_prompt(
        "CPU Scheduling", "Keep it under 2 sentences", ["PLO-3 (Problem Analysis): desc"]
    )
    assert "CPU Scheduling" in prompt
    assert "Keep it under 2 sentences" in prompt
    assert "PLO-3" in prompt


def test_get_client_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    clo_generator._client = None
    with pytest.raises(LLMGenerationError):
        clo_generator.get_client()


async def test_agenerate_clo_suggestion_success(monkeypatch):
    fake = _FakeClient(
        content='{"title": "Apply Sorting", "description": "Implement sorting algorithms.", "bloom_level": "Apply"}'
    )
    monkeypatch.setattr(clo_generator, "get_client", lambda: fake)

    result = await clo_generator.agenerate_clo_suggestion("Sorting", "", ["PLO-2: desc"])
    assert result.title == "Apply Sorting"
    assert result.bloom_level == "Apply"


async def test_agenerate_clo_suggestion_wraps_client_errors(monkeypatch):
    fake = _FakeClient(error=RuntimeError("network down"))
    monkeypatch.setattr(clo_generator, "get_client", lambda: fake)

    with pytest.raises(LLMGenerationError):
        await clo_generator.agenerate_clo_suggestion("Sorting", "", ["PLO-2: desc"])


async def test_agenerate_clo_suggestion_empty_response(monkeypatch):
    fake = _FakeClient(content=None)
    monkeypatch.setattr(clo_generator, "get_client", lambda: fake)

    with pytest.raises(LLMGenerationError):
        await clo_generator.agenerate_clo_suggestion("Sorting", "", ["PLO-2: desc"])
