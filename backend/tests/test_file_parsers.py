"""app/services/file_parsers.py -- pure, no DB/HTTP, mirrors the discipline
of attainment_math.py's test file.

Regression coverage for a real bug found via manual testing: a multi-page
PDF table built with reportlab's `repeatRows=1` (redraws the header row at
the top of every page for readability -- used throughout this codebase's
generated exam papers/rosters/templates) gets its header extracted again by
pdfplumber on every page after the first, which previously became a phantom
"student" row exactly matching the column headers.
"""

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from app.services import file_parsers


def build_multipage_pdf(header: list[str], rows: list[list[str]]) -> bytes:
    """A minimal reportlab table with `repeatRows=1` and enough rows to
    force a real page break, so the header genuinely gets redrawn -- not a
    hand-crafted duplicate. A GRID style is required for pdfplumber's
    default line-based table detection to find it at all (matches every
    real generated file in this repo, which are always gridded)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    table = Table([header] + rows, repeatRows=1)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, (0, 0, 0))]))
    doc.build([table])
    return buffer.getvalue()


def test_parse_pdf_drops_repeated_header_on_page_break():
    header = ["Full Name", "Seat No", "Marks"]
    # Enough rows that A4 + default margins forces at least one page break.
    rows = [[f"Student {i}", f"SEAT-{i:03d}", "5"] for i in range(80)]
    content = build_multipage_pdf(header, rows)

    parsed = file_parsers.parse_pdf(content)

    assert parsed[0] == header
    # No row after the header should ever equal the header again.
    assert all(row != header for row in parsed[1:])
    assert len(parsed) == 1 + len(rows)


def test_parse_pdf_single_page_unaffected():
    header = ["Full Name", "Seat No", "Marks"]
    rows = [["Abdul Aziz", "SEAT-001", "5"], ["Zain Iqbal", "SEAT-002", "4"]]
    content = build_multipage_pdf(header, rows)

    parsed = file_parsers.parse_pdf(content)

    assert parsed == [header, *rows]


def test_parse_pdf_real_student_row_never_dropped_unless_identical_to_header():
    header = ["Full Name", "Seat No", "Marks"]
    # A row that merely shares one cell's text with the header ("Marks" as
    # someone's seat number, implausible but a good adversarial case) must
    # still survive -- only a row identical across *every* column is a
    # repeated-header artifact.
    rows = [["Marks", "SEAT-777", "3"]]
    content = build_multipage_pdf(header, rows)

    parsed = file_parsers.parse_pdf(content)

    assert parsed == [header, *rows]
