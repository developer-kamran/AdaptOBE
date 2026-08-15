"""Turn an uploaded roster file into raw table rows.

Deliberately knows nothing about students, the database, or HTTP -- it takes
bytes in and returns `list[list[str]]` out, first row being the header row.
That keeps it unit-testable without a DB or a request, the same way
`attainment_math.py` is.
"""

from io import BytesIO

#: Refuse absurdly large sheets rather than trying to parse them. A single
#: department's intake is nowhere near this.
MAX_ROWS = 2000

EXCEL_EXTENSIONS = (".xlsx", ".xls")
PDF_EXTENSIONS = (".pdf",)
SUPPORTED_EXTENSIONS = EXCEL_EXTENSIONS + PDF_EXTENSIONS


class FileParseError(Exception):
    """Raised when a file cannot be read at all (corrupt, wrong format)."""


def _clean(value) -> str:
    """Normalize any cell to a trimmed string. `None` and numeric cells are
    both common in spreadsheets -- an enrollment number typed as a number
    must not become '12345.0'."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _is_blank_row(row: list[str]) -> bool:
    return all(cell == "" for cell in row)


def _trim_trailing_blank_columns(rows: list[list[str]]) -> list[list[str]]:
    """Spreadsheets often report a wider used-range than has real data."""
    width = 0
    for row in rows:
        for index, cell in enumerate(row):
            if cell != "":
                width = max(width, index + 1)
    if width == 0:
        return []
    return [row[:width] + [""] * (width - len(row[:width])) for row in rows]


def parse_excel(content: bytes) -> list[list[str]]:
    """Read the first worksheet of an .xlsx/.xls file into rows.

    `data_only=True` returns the cached *value* of a formula cell rather than
    the formula text, which is what a roster exported from another system
    typically contains.
    """
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises a variety of types on bad input
        raise FileParseError("This file could not be read as an Excel workbook") from exc

    try:
        worksheet = workbook.worksheets[0]
        rows: list[list[str]] = []
        for raw_row in worksheet.iter_rows(values_only=True):
            row = [_clean(cell) for cell in raw_row]
            if _is_blank_row(row):
                continue
            rows.append(row)
            if len(rows) >= MAX_ROWS:
                break
    finally:
        workbook.close()

    return _trim_trailing_blank_columns(rows)


def parse_pdf(content: bytes) -> list[list[str]]:
    """Extract tabular rows from a PDF.

    Only real tables are read. If the document has no detectable table we
    return nothing rather than guessing at free-form text -- a wrong guess
    here would silently create students with garbage data, which is worse
    than telling the user the file isn't usable.
    """
    import pdfplumber

    rows: list[list[str]] = []
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for raw_row in table:
                        row = [_clean(cell) for cell in raw_row]
                        if _is_blank_row(row):
                            continue
                        rows.append(row)
                        if len(rows) >= MAX_ROWS:
                            return _trim_trailing_blank_columns(rows)
    except FileParseError:
        raise
    except Exception as exc:
        raise FileParseError("This file could not be read as a PDF") from exc

    return _trim_trailing_blank_columns(rows)


def parse_file(content: bytes, filename: str) -> list[list[str]]:
    """Dispatch on file extension. Caller is expected to have already
    rejected unsupported extensions, but this stays defensive."""
    lowered = filename.lower()
    if lowered.endswith(EXCEL_EXTENSIONS):
        return parse_excel(content)
    if lowered.endswith(PDF_EXTENSIONS):
        return parse_pdf(content)
    raise FileParseError(
        f"Unsupported file type. Upload one of: {', '.join(SUPPORTED_EXTENSIONS)}"
    )
