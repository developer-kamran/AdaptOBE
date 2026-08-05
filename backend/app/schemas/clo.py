from pydantic import BaseModel, ConfigDict, Field


class CLOCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    bloom_level: str | None = Field(default=None, max_length=50)


class CLOUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    bloom_level: str | None = Field(default=None, max_length=50)


class CLORead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    code: str
    title: str
    description: str
    bloom_level: str | None
