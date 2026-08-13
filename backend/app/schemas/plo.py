import enum

from pydantic import BaseModel, ConfigDict, Field


class PLODomain(str, enum.Enum):
    """Bloom's three learning domains -- matches the literal strings already
    seeded for all 40 institutional PLOs in app/core/institution.py."""

    cognitive = "Cognitive"
    psychomotor = "Psychomotor"
    affective = "Affective"


class PLOCreate(BaseModel):
    program_id: int
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    domain: PLODomain | None = None


class PLOUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    domain: PLODomain | None = None


class PLORead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: int
    code: str
    title: str
    description: str
    domain: str | None
