from pydantic import BaseModel

from app.models.question import QuestionType


class DetectedField(BaseModel):
    """One verification check (Section 4 of the feature spec: Assessment
    Title, Course, Course Code, Instructor). `detected` is whatever the AI
    read off the uploaded document for this field (None if it found
    nothing); `expected` is the current assessment/course/instructor's real
    value; `matches` is a fuzzy comparison of the two."""

    detected: str | None
    expected: str
    matches: bool


class AssessmentPaperVerification(BaseModel):
    course_name: DetectedField
    course_code: DetectedField
    assessment_title: DetectedField
    instructor: DetectedField
    all_matched: bool


class ExtractedQuestionRow(BaseModel):
    """One AI-suggested question, ready for the faculty to review/edit
    before any of it is written. `question_number` here is just a display
    ordinal (extraction order) -- the actual number assigned on import is
    decided by the faculty/frontend against the assessment's real numbering,
    same as the manual bulk-create flow.

    `clo_id` is only ever a *starting suggestion* -- populated when the
    document itself marks a CLO next to the question and that mark matches
    one of this course's real CLOs. The faculty can freely change it (or use
    "Suggest with AI", same as manual question entry) before confirming;
    this never bypasses that manual step."""

    question_number: int
    question_type: QuestionType
    text: str
    marks: float | None
    type_data: dict | None
    clo_id: int | None = None


class AssessmentPaperPreview(BaseModel):
    verification: AssessmentPaperVerification
    questions: list[ExtractedQuestionRow]
    warnings: list[str] = []
