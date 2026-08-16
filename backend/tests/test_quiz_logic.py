"""Pure unit tests for adaptive-quiz slot allocation and grading."""

from app.models.question import QuestionType
from app.services import quiz_logic


def test_weaker_clo_gets_more_slots():
    # CLO 1 is much weaker (90) than CLO 2 (10); both have plenty of questions.
    # The weak CLO should dominate the quiz (here it takes all of it).
    alloc = quiz_logic.allocate_quiz_slots(
        weakness={1: 90.0, 2: 10.0}, available={1: 10, 2: 10}, total=6
    )
    assert alloc.get(1, 0) > alloc.get(2, 0)
    assert sum(alloc.values()) == 6

    # With closer weakness the split is shared but still tilts to the weaker one.
    alloc2 = quiz_logic.allocate_quiz_slots(
        weakness={1: 60.0, 2: 40.0}, available={1: 10, 2: 10}, total=5
    )
    assert alloc2.get(1, 0) >= alloc2.get(2, 0)
    assert sum(alloc2.values()) == 5


def test_allocation_never_exceeds_available():
    alloc = quiz_logic.allocate_quiz_slots(
        weakness={1: 100.0, 2: 50.0}, available={1: 2, 2: 3}, total=10
    )
    assert alloc[1] == 2  # capped at what exists
    assert alloc[2] == 3
    assert sum(alloc.values()) == 5  # only 5 questions exist total


def test_allocation_skips_clos_with_no_questions():
    alloc = quiz_logic.allocate_quiz_slots(
        weakness={1: 100.0, 2: 100.0}, available={1: 0, 2: 4}, total=3
    )
    assert 1 not in alloc
    assert alloc[2] == 3


def test_missing_weakness_treated_as_weakest():
    # CLO 2 has no attainment record -> defaults to max weakness -> favoured.
    alloc = quiz_logic.allocate_quiz_slots(
        weakness={1: 20.0}, available={1: 5, 2: 5}, total=4
    )
    assert alloc.get(2, 0) >= alloc.get(1, 0)


def test_grade_mcq():
    data = {"options": [{"label": "A"}, {"label": "B"}], "correct_option": "B"}
    assert quiz_logic.grade_answer(QuestionType.mcq, data, "B") is True
    assert quiz_logic.grade_answer(QuestionType.mcq, data, "b") is True  # case-insensitive
    assert quiz_logic.grade_answer(QuestionType.mcq, data, "A") is False


def test_grade_true_false():
    data = {"correct_answer": True}
    assert quiz_logic.grade_answer(QuestionType.true_false, data, True) is True
    assert quiz_logic.grade_answer(QuestionType.true_false, data, "true") is True
    assert quiz_logic.grade_answer(QuestionType.true_false, data, False) is False


def test_grade_fill_blank():
    data = {"answer": "Polymorphism"}
    assert quiz_logic.grade_answer(QuestionType.fill_blank, data, " polymorphism ") is True
    assert quiz_logic.grade_answer(QuestionType.fill_blank, data, "inheritance") is False


def test_grade_is_total_on_missing_input():
    assert quiz_logic.grade_answer(QuestionType.mcq, None, "A") is False
    assert quiz_logic.grade_answer(QuestionType.mcq, {"correct_option": "A"}, None) is False
    # Free-form questions are never auto-graded.
    assert quiz_logic.grade_answer(QuestionType.question, {"answer": "x"}, "x") is False
