from pydantic import BaseModel, ConfigDict, Field


class EnrollmentCreate(BaseModel):
    student_ids: list[int] = Field(min_length=1)


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    student_id: int
