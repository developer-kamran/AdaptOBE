from pydantic import BaseModel, ConfigDict, Field


class ProgramCreate(BaseModel):
    dept_id: int
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    total_semesters: int = Field(gt=0)


class ProgramUpdate(BaseModel):
    dept_id: int | None = None
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    total_semesters: int | None = Field(default=None, gt=0)


class ProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dept_id: int
    code: str
    name: str
    total_semesters: int
