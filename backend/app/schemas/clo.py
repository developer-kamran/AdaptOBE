from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: The six standard Bloom's Taxonomy (cognitive domain) levels. A CLO must be
#: tagged with exactly one of these at creation time.
BLOOM_LEVELS: tuple[str, ...] = (
    "Remember",
    "Understand",
    "Apply",
    "Analyze",
    "Evaluate",
    "Create",
)

BloomLevel = Literal[
    "Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"
]


class CLOCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    bloom_level: BloomLevel


class CLOUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    # Optional on update (existing CLOs may predate this requirement), but
    # still restricted to the standard six when supplied.
    bloom_level: BloomLevel | None = None


class CLORead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    code: str
    title: str
    description: str
    bloom_level: str | None
