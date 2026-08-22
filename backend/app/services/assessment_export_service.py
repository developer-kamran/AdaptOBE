"""Per-assessment exam-paper export (PDF/Word) -- distinct from the course-level
attainment PDF/Excel export in `report_service.py`, which stays untouched.

This renders an actual printable exam paper (course/assessment header, meta
info, then numbered questions), not a data-dump table -- so it deliberately
does not reuse `report_service._styled_table`, whose tabular shape doesn't fit
an exam layout. Correct answers are never printed: this is meant to be handed
to students.
"""

import io

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.course import Course
from app.models.assessment import Assessment
from app.models.question import Question, QuestionType

_OPTION_LABELS = "ABCDEFGH"


def _format_duration(minutes: int | None) -> str:
    if not minutes:
        return "—"
    return f"{minutes} minutes"


def _format_date(value) -> str:
    if not value:
        return "—"
    return value.strftime("%B %d, %Y")


def _question_lines(question: Question) -> list[str]:
    """Answer-space lines to render under a question -- never the answer itself."""
    if question.question_type == QuestionType.mcq:
        options = (question.type_data or {}).get("options") or []
        return [
            f"{_OPTION_LABELS[i] if i < len(_OPTION_LABELS) else i + 1}. {opt.get('text', '')}"
            for i, opt in enumerate(options)
        ]
    if question.question_type == QuestionType.true_false:
        return ["True  /  False"]
    if question.question_type == QuestionType.fill_blank:
        return ["Answer: ______________________________________"]
    return []


def build_exam_pdf(
    course: Course, assessment: Assessment, instructor_name: str, questions: list[Question]
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, topMargin=0.8 * inch, bottomMargin=0.8 * inch,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ExamTitle", parent=styles["Title"], alignment=TA_CENTER)
    subtitle_style = ParagraphStyle(
        "ExamSubtitle", parent=styles["Heading2"], alignment=TA_CENTER, spaceBefore=0
    )
    answer_style = ParagraphStyle(
        "AnswerLine", parent=styles["Normal"], leftIndent=0.28 * inch, spaceBefore=2
    )

    # Both the meta box and every question row are built to this exact width,
    # so their right-hand edges line up with each other instead of the
    # question rows falling short of the meta box's right border.
    content_width = doc.width
    marks_col_width = 0.6 * inch

    story = [
        Paragraph(course.name, title_style),
        Paragraph(assessment.title, subtitle_style),
        Spacer(1, 0.2 * inch),
        _meta_table(course, assessment, instructor_name, content_width),
        Spacer(1, 0.3 * inch),
    ]

    for question in sorted(questions, key=lambda q: q.question_number):
        story.append(
            Table(
                [[
                    Paragraph(f"<b>Q{question.question_number}.</b> {question.text or ''}", styles["Normal"]),
                    Paragraph(f"<b>[{question.marks:g}]</b>", styles["Normal"]),
                ]],
                colWidths=[content_width - marks_col_width, marks_col_width],
                style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
            )
        )
        for line in _question_lines(question):
            story.append(Paragraph(line, answer_style))
        story.append(Spacer(1, 0.22 * inch))

    if not questions:
        story.append(Paragraph("No questions have been added to this assessment yet.", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()


def _meta_table(course: Course, assessment: Assessment, instructor_name: str, content_width: float) -> Table:
    """A 3-row x 2-column boxed grid -- each field in its own bordered cell,
    matching the original single-row boxed-field look, just regrouped:
    Total Marks / Course Code / Instructor on the left, Allocated Time / Date
    on the right (the fourth cell is left blank since the left column has one
    more field than the right)."""
    left_style = ParagraphStyle("MetaLeft", fontSize=9, leading=13, alignment=TA_LEFT)
    right_style = ParagraphStyle("MetaRight", fontSize=9, leading=13, alignment=TA_RIGHT)

    rows = [
        [
            Paragraph(f"<b>Total Marks:</b> {assessment.total_marks:g}", left_style),
            Paragraph(f"<b>Allocated Time:</b> {_format_duration(assessment.duration_minutes)}", right_style),
        ],
        [
            Paragraph(f"<b>Course Code:</b> {course.code}", left_style),
            Paragraph(f"<b>Date:</b> {_format_date(assessment.date)}", right_style),
        ],
        [
            Paragraph(f"<b>Instructor:</b> {instructor_name}", left_style),
            "",
        ],
    ]

    half_width = content_width / 2
    table = Table(rows, colWidths=[half_width, half_width], hAlign="CENTER")
    table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (0, -1), 10),
            ("RIGHTPADDING", (-1, 0), (-1, -1), 10),
        ])
    )
    return table


def build_exam_docx(
    course: Course, assessment: Assessment, instructor_name: str, questions: list[Question]
) -> bytes:
    document = Document()

    title = document.add_heading(course.name, level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_heading(assessment.title, level=2)
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta_table = document.add_table(rows=1, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    left_cell, right_cell = meta_table.rows[0].cells

    left_lines = [
        f"Total Marks: {assessment.total_marks:g}",
        f"Course Code: {course.code}",
        f"Instructor: {instructor_name}",
    ]
    left_cell.paragraphs[0].add_run(left_lines[0]).bold = True
    for line in left_lines[1:]:
        para = left_cell.add_paragraph()
        para.add_run(line).bold = True

    right_lines = [
        f"Allocated Time: {_format_duration(assessment.duration_minutes)}",
        f"Date: {_format_date(assessment.date)}",
    ]
    right_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right_cell.paragraphs[0].add_run(right_lines[0]).bold = True
    for line in right_lines[1:]:
        para = right_cell.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        para.add_run(line).bold = True

    document.add_paragraph()

    if not questions:
        document.add_paragraph("No questions have been added to this assessment yet.")

    for question in sorted(questions, key=lambda q: q.question_number):
        para = document.add_paragraph()
        run = para.add_run(f"Q{question.question_number}. {question.text or ''}")
        run.font.size = Pt(11)
        marks_run = para.add_run(f"   [{question.marks:g}]")
        marks_run.bold = True

        for line in _question_lines(question):
            document.add_paragraph(line, style="List Bullet" if question.question_type == QuestionType.mcq else None)
        document.add_paragraph()

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
