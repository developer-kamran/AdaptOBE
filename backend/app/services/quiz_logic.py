"""Pure adaptive-quiz logic: slot allocation and answer grading.

Framework-free so the difficulty-scaling and grading rules can be unit-tested
without a database or the question models, matching the discipline of
`attainment_math.py` / `risk_math.py`.

`type_data` shapes (see schemas/question.py):
  mcq:         { options: [{label, text}], correct_option }
  fill_blank:  { answer }
  true_false:  { correct_answer: bool }
"""

from app.models.question import QuestionType

# Only these question types are auto-gradable (they carry a machine-checkable
# answer in `type_data`); free-form `question`, and the `lab`/`project`
# assessment components, are excluded from adaptive quizzes.
AUTO_GRADABLE_TYPES = (QuestionType.mcq, QuestionType.true_false, QuestionType.fill_blank)

DEFAULT_QUIZ_SIZE = 5


def allocate_quiz_slots(
    weakness: dict[int, float],
    available: dict[int, int],
    total: int,
) -> dict[int, int]:
    """Distribute `total` quiz slots across CLOs, favouring weaker ones.

    `weakness[clo]` is 0-100 (higher = weaker, i.e. lower attainment), and
    `available[clo]` caps how many questions actually exist for that CLO. A CLO
    with no attainment record should be passed in at max weakness by the caller.

    Greedy and deterministic: each slot goes to the CLO with the highest
    weight-per-slot-so-far that still has questions left, so weaker CLOs get
    more questions while no CLO exceeds its available pool.
    """
    clos = [clo for clo, count in available.items() if count > 0]
    # A mastered CLO still keeps a floor weight of 1 so it can appear if there
    # is room left over after the weak ones are exhausted.
    weights = {clo: max(weakness.get(clo, 100.0), 1.0) for clo in clos}

    alloc = {clo: 0 for clo in clos}
    remaining = min(total, sum(available[clo] for clo in clos))

    while remaining > 0:
        candidates = [clo for clo in clos if alloc[clo] < available[clo]]
        if not candidates:
            break
        # Highest weight-per-next-slot wins; tie-break on clo id for determinism.
        chosen = max(candidates, key=lambda clo: (weights[clo] / (alloc[clo] + 1), -clo))
        alloc[chosen] += 1
        remaining -= 1

    return {clo: count for clo, count in alloc.items() if count > 0}


def _normalize(value) -> str:
    return str(value).strip().lower()


def grade_answer(question_type: QuestionType, type_data: dict | None, answer) -> bool:
    """Whether `answer` is correct for a question of the given type.

    Total and defensive: a missing answer, missing `type_data`, or unsupported
    type simply grades as incorrect rather than raising.
    """
    if not type_data or answer is None:
        return False

    if question_type == QuestionType.mcq:
        return _normalize(answer) == _normalize(type_data.get("correct_option"))

    if question_type == QuestionType.true_false:
        expected = type_data.get("correct_answer")
        if isinstance(answer, bool):
            return answer == bool(expected)
        # Accept "true"/"false" strings too.
        return _normalize(answer) == _normalize(expected)

    if question_type == QuestionType.fill_blank:
        return _normalize(answer) == _normalize(type_data.get("answer"))

    return False
