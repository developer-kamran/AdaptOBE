"""Pure attainment mathematics (CLAUDE.md section 8).

Deliberately free of database and framework imports so the formulas can be
unit-tested in isolation. Every function is total: no input combination raises
ZeroDivisionError; degenerate denominators yield 0.0 and log a warning.
"""

import logging

logger = logging.getLogger(__name__)


def clo_attainment(marks_obtained: float, marks_possible: float) -> float:
    """CLO attainment % = (obtained / possible) * 100.

    `marks_possible` of 0 means no CLO-tagged questions carried any marks, so
    there is nothing to attain; section 8 requires 0.00 rather than an error.
    """
    if marks_possible <= 0:
        logger.warning(
            "CLO attainment requested with non-positive possible marks (%s); returning 0.0",
            marks_possible,
        )
        return 0.0

    return round((marks_obtained / marks_possible) * 100.0, 2)


def plo_attainment(contributions: list[tuple[float, int]]) -> float:
    """PLO attainment % = sum(clo_attainment * strength) / sum(strength).

    `contributions` is a list of (clo_attainment_percentage, mapping_strength).
    An empty list, or strengths summing to 0, yields 0.00 per section 8.
    """
    total_strength = sum(strength for _, strength in contributions)

    if total_strength <= 0:
        logger.warning(
            "PLO attainment requested with total mapping strength %s; returning 0.0",
            total_strength,
        )
        return 0.0

    weighted = sum(attainment * strength for attainment, strength in contributions)
    return round(weighted / total_strength, 2)


def class_average(values: list[float]) -> float:
    """Mean attainment across a cohort.

    Callers must pass one value per *enrolled* student, including absentees
    scored 0.0, so the denominator is never silently shrunk (section 8).
    """
    if not values:
        logger.warning("Class average requested with no enrolled students; returning 0.0")
        return 0.0

    return round(sum(values) / len(values), 2)


def is_achieved(class_average_percentage: float, threshold: float) -> bool:
    """A CLO counts as achieved when the class average reaches the threshold."""
    return class_average_percentage >= threshold
