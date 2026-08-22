from pydantic import BaseModel, Field

from app.schemas.clo import BloomLevel


class GenerateCloRequest(BaseModel):
    target_plo_ids: list[int] = Field(min_length=1)
    topic: str = Field(min_length=1, max_length=500)
    requirements: str = Field(default="", max_length=2000)


class GenerateCloResponse(BaseModel):
    title: str
    description: str
    bloom_level: BloomLevel
