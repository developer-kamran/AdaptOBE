from pydantic import BaseModel, ConfigDict, Field


class QuestionCreate(BaseModel):
    question_number: int = Field(gt=0)
    marks: float = Field(ge=0)
    clo_id: int | None = None
    text: str | None = None


class QuestionUpdate(BaseModel):
    question_number: int | None = Field(default=None, gt=0)
    marks: float | None = Field(default=None, ge=0)
    clo_id: int | None = None
    text: str | None = None


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int
    question_number: int
    marks: float
    clo_id: int | None
    text: str | None


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
