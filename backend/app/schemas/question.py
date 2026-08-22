from pydantic import BaseModel, ConfigDict, Field

from app.models.question import QuestionType

#: Loose (not discriminated-union) shape convention for `type_data`, kept
#: intentionally simple per product direction -- see models/question.py:
#:   mcq:         { options: [{label, text}], correct_option }
#:   fill_blank:  { answer }
#:   true_false:  { correct_answer: bool }
#:   project:     { description, deliverable? }
#:   lab:         { description, tasks? }


class QuestionCreate(BaseModel):
    question_number: int = Field(gt=0)
    marks: float = Field(gt=0)
    clo_id: int | None = None
    text: str = Field(min_length=1)
    question_type: QuestionType = QuestionType.question
    type_data: dict | None = None


class QuestionUpdate(BaseModel):
    question_number: int | None = Field(default=None, gt=0)
    marks: float | None = Field(default=None, gt=0)
    clo_id: int | None = None
    text: str | None = Field(default=None, min_length=1)
    question_type: QuestionType | None = None
    type_data: dict | None = None


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int
    question_number: int
    marks: float
    clo_id: int | None
    text: str | None
    question_type: QuestionType
    type_data: dict | None


class QuestionBulkCreateRequest(BaseModel):
    items: list[QuestionCreate] = Field(min_length=1)


class QuestionBulkCreateResponse(BaseModel):
    created: list[QuestionRead]


class TagSuggestRequest(BaseModel):
    """Ask the model which CLO a question's wording best matches."""

    text: str = Field(min_length=1)
    limit: int = Field(default=3, ge=1, le=10)


class CLOTagSuggestion(BaseModel):
    clo_id: int
    code: str
    title: str
    similarity_score: float


class TagSuggestResponse(BaseModel):
    suggestions: list[CLOTagSuggestion]
