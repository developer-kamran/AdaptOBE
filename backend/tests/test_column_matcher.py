"""Pure tests for app/ml/column_matcher.py -- the score-column matching path
(no DB, no embedding model) plus the prompt-cache correctness fix."""

import gc

import pytest

from app.ml import column_matcher, embeddings


class _Q:
    def __init__(self, id, number):
        self.id = id
        self.question_number = number


def test_match_question_columns_alias_hits():
    questions = [_Q(101, 1), _Q(102, 2), _Q(103, 3)]
    headers = ["Name", "Seat No", "Q1", "Question 2", "Marks Q3"]
    result = column_matcher.match_question_columns(headers, questions, excluded_columns={0, 1})

    assert result[101].index == 2 and result[101].matched_by == "alias"
    assert result[102].index == 3 and result[102].matched_by == "alias"
    assert result[103].index == 4 and result[103].matched_by == "alias"


def test_match_question_columns_positional_fallback():
    questions = [_Q(101, 1), _Q(102, 2), _Q(103, 3)]
    headers = ["Name", "Seat No", "Part A", "Part B", "Part C"]
    result = column_matcher.match_question_columns(headers, questions, excluded_columns={0, 1})

    assert result[101].index == 2 and result[101].matched_by == "position"
    assert result[102].index == 3 and result[102].matched_by == "position"
    assert result[103].index == 4 and result[103].matched_by == "position"


def test_match_question_columns_no_positional_guess_on_count_mismatch():
    """Ambiguous leftover counts should never be guessed at."""
    questions = [_Q(101, 1), _Q(102, 2)]
    headers = ["Name", "Part A", "Part B", "Part C"]  # 3 leftover columns, 2 leftover questions
    result = column_matcher.match_question_columns(headers, questions, excluded_columns=set())

    assert result[101].index is None
    assert result[102].index is None


def test_match_question_columns_never_uses_embeddings(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("embeddings must never be used for question-column matching")

    monkeypatch.setattr(embeddings, "encode_text", boom)

    questions = [_Q(101, 1), _Q(102, 2), _Q(103, 3), _Q(104, 4)]
    headers = ["Name", "Q1", "Q2", "Q3", "Q4"]
    result = column_matcher.match_question_columns(headers, questions, excluded_columns={0})
    assert all(m.index is not None for m in result.values())


async def test_prompt_cache_survives_short_lived_dict_id_reuse():
    """Regression test for the id()-based cache bug: two structurally
    different but transient field-prompt dicts must never cross-contaminate,
    even if Python reuses a freed dict's id() for the next one."""
    first = {"a": "alpha description"}
    second = {"a": "beta description entirely different"}

    encoded_first = column_matcher._encode_prompts(first)["a"]
    del first
    gc.collect()  # encourage id() reuse for `second`, if the bug were present
    encoded_second = column_matcher._encode_prompts(second)["a"]

    # Different content must yield different (correctly re-encoded) vectors --
    # under the old id()-keyed cache this could wrongly return `encoded_first`.
    assert encoded_first != encoded_second
