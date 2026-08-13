"""Pure functions for computing a course's expected student batch (seat
number year) from its semester, and classifying a given seat number as
current-batch, backlog, or unparseable. No DB, no HTTP -- see
app/core/institution.py."""

from app.core.institution import (
    expected_seat_no_prefix,
    expected_seat_no_year,
    is_backlog_batch_year,
    seat_no_batch_year,
)


class TestExpectedSeatNoYear:
    def test_semester_four_is_two_years_back(self):
        assert expected_seat_no_year(4, reference_year=2026) == 2024

    def test_semester_eight_is_four_years_back(self):
        assert expected_seat_no_year(8, reference_year=2026) == 2022

    def test_semester_one_is_the_reference_year_itself(self):
        assert expected_seat_no_year(1, reference_year=2026) == 2026

    def test_semester_two_is_one_year_back(self):
        assert expected_seat_no_year(2, reference_year=2026) == 2025

    def test_defaults_to_the_real_current_year_when_unspecified(self):
        import datetime

        assert expected_seat_no_year(2) == datetime.date.today().year - 1


class TestExpectedSeatNoPrefix:
    def test_known_program_builds_the_full_prefix(self):
        assert expected_seat_no_prefix("BSSE", 4, reference_year=2026) == "B241101"

    def test_semester_eight_reaches_further_back(self):
        assert expected_seat_no_prefix("BSSE", 8, reference_year=2026) == "B221101"

    def test_different_programs_get_different_codes_same_year(self):
        assert expected_seat_no_prefix("BSCS", 4, reference_year=2026) == "B241100"
        assert expected_seat_no_prefix("BSAI", 4, reference_year=2026) == "B241102"
        assert expected_seat_no_prefix("BSDS", 4, reference_year=2026) == "B241103"

    def test_unknown_program_code_returns_none(self):
        assert expected_seat_no_prefix("BSSE-TEST", 4, reference_year=2026) is None


class TestSeatNoBatchYear:
    def test_parses_the_two_digit_year(self):
        assert seat_no_batch_year("B221101-0001") == 2022

    def test_parses_regardless_of_trailing_shape(self):
        assert seat_no_batch_year("B24110106001") == 2024

    def test_none_for_missing_value(self):
        assert seat_no_batch_year(None) is None

    def test_none_for_too_short_value(self):
        assert seat_no_batch_year("B2") is None

    def test_none_when_it_does_not_start_with_b(self):
        assert seat_no_batch_year("X221101-0001") is None

    def test_none_when_year_segment_is_not_digits(self):
        assert seat_no_batch_year("BXX1101-0001") is None


class TestIsBacklogBatchYear:
    def test_true_for_a_student_from_an_earlier_batch(self):
        assert is_backlog_batch_year("B221101-0001", semester=4, reference_year=2026) is True

    def test_false_for_a_current_batch_student(self):
        assert is_backlog_batch_year("B241101-0001", semester=4, reference_year=2026) is False

    def test_false_for_a_student_from_a_later_batch_than_expected(self):
        assert is_backlog_batch_year("B251101-0001", semester=4, reference_year=2026) is False

    def test_false_when_seat_no_does_not_parse(self):
        assert is_backlog_batch_year("SEAT-NOPARSE", semester=4, reference_year=2026) is False

    def test_false_for_none(self):
        assert is_backlog_batch_year(None, semester=4, reference_year=2026) is False
