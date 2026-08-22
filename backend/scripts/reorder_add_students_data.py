"""One-off data fix: reorder data/add_students/*.xlsx + *.pdf alphabetically
by Full Name and reassign Seat No sequentially in that order (so "Abdul..."
gets the first seat number and a "Z..." name gets the last), instead of the
previous effectively-random seat assignment.

Not part of the running app -- this is a data-file regeneration utility, run
once by hand:

    python scripts/reorder_add_students_data.py

Only Seat No is reassigned. Full Name, Father's Name, Enrollment No, and
Email/Eligible stay attached to whichever student they already belonged to --
they're per-student identifiers, not position-derived.
"""

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "add_students"

#: The seat-number prefix used throughout this sample data (see
#: app/core/institution.py -- "B" + 2-digit year + BSSE's "1101" code + a
#: fixed "06" segment for this particular dataset). Only the trailing 3-digit
#: roll number changes.
SEAT_NO_PREFIX = "B22110106"


def _seat_no(position: int) -> str:
    return f"{SEAT_NO_PREFIX}{position:03d}"


def reorder_rows(rows: list[tuple], seat_col_index: int) -> list[list]:
    """`rows` excludes the header. Sorts by Full Name (column 0), then
    rewrites the Seat No column (`seat_col_index`) to a fresh sequential
    value in that new order."""
    sorted_rows = sorted(rows, key=lambda r: str(r[0]).strip().lower())
    result = []
    for position, row in enumerate(sorted_rows, start=1):
        new_row = list(row)
        new_row[seat_col_index] = _seat_no(position)
        result.append(new_row)
    return result


def process_excel(path: Path) -> tuple[list, list[list]]:
    wb = load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    all_rows = list(ws.iter_rows(values_only=True))
    header, *data_rows = all_rows
    seat_col_index = header.index("Seat No")
    reordered = reorder_rows(data_rows, seat_col_index)
    return list(header), reordered


def write_excel(path: Path, header: list, rows: list[list]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    for column_cells in ws.columns:
        max_len = max(len(str(c.value)) if c.value is not None else 0 for c in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = max(12, max_len + 2)
    wb.save(path)


def write_pdf(path: Path, header: list, rows: list[list]) -> None:
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch, leftMargin=0.5 * inch, rightMargin=0.5 * inch,
    )
    table_data = [header] + [[str(v) if v is not None else "" for v in row] for row in rows]
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    doc.build([table])


def main():
    pairs = [
        ("BSSE_students.xlsx", "BSSE_students.pdf"),
        ("enroll_bsse_students.xlsx", "enroll_bsse_students.pdf"),
    ]
    for xlsx_name, pdf_name in pairs:
        xlsx_path = DATA_DIR / xlsx_name
        pdf_path = DATA_DIR / pdf_name
        header, rows = process_excel(xlsx_path)
        write_excel(xlsx_path, header, rows)
        write_pdf(pdf_path, header, rows)
        print(f"Reordered {len(rows)} rows -> {xlsx_name}, {pdf_name}")


if __name__ == "__main__":
    main()
