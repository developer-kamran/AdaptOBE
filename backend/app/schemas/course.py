from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    program_id: int
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    credit_hours: int = Field(gt=0)
    semester: int = Field(gt=0)


class CourseUpdate(BaseModel):
    program_id: int | None = None
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    credit_hours: int | None = Field(default=None, gt=0)
    semester: int | None = Field(default=None, gt=0)


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: int
    owner_faculty_id: int
    code: str
    name: str
    credit_hours: int
    semester: int
