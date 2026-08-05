from pydantic import BaseModel, ConfigDict, Field


class ScoreEntry(BaseModel):
    question_id: int
    student_id: int
    marks_obtained: float = Field(ge=0)


class BulkScoreRequest(BaseModel):
    scores: list[ScoreEntry] = Field(min_length=1)


class ScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    student_id: int
    marks_obtained: float


class BulkScoreResponse(BaseModel):
    saved: int
    recalculated_students: int
