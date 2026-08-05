from pydantic import BaseModel, ConfigDict, Field


class PLOCreate(BaseModel):
    program_id: int
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    domain: str | None = Field(default=None, max_length=100)


class PLOUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    domain: str | None = Field(default=None, max_length=100)


class PLORead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: int
    code: str
    title: str
    description: str
    domain: str | None
