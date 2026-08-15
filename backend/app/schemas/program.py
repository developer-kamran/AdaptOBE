from pydantic import BaseModel, ConfigDict, Field


class ProgramCreate(BaseModel):
    # Optional: the only caller who can create a programme is a sub_admin,
    # and the service always forces this to their own department regardless
    # of what's sent here.
    dept_id: int | None = None
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
