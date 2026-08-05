from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field

from app.models.assessment import AssessmentType


class AssessmentCreate(BaseModel):
    course_id: int
    title: str = Field(min_length=1, max_length=255)
    type: AssessmentType
    total_marks: float = Field(ge=0)
    weightage_percent: float = Field(ge=0, le=100)
    date: date_type | None = None


class AssessmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    type: AssessmentType | None = None
    total_marks: float | None = Field(default=None, ge=0)
    weightage_percent: float | None = Field(default=None, ge=0, le=100)
    date: date_type | None = None


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    type: AssessmentType
    total_marks: float
    weightage_percent: float
    date: date_type | None
