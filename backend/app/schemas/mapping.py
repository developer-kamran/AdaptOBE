from pydantic import BaseModel, ConfigDict, Field


class MappingSuggestRequest(BaseModel):
    clo_id: int
    limit: int = Field(default=3, ge=1, le=10)


class PLOSuggestion(BaseModel):
    plo_id: int
    code: str
    title: str
    description: str
    similarity_score: float


class MappingSuggestResponse(BaseModel):
    clo_id: int
    suggestions: list[PLOSuggestion]


class MappingConfirmRequest(BaseModel):
    clo_id: int
    plo_id: int
    strength: int = Field(ge=1, le=3)
    is_ai_generated: bool = False
    similarity_score: float | None = None


class MappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clo_id: int
    plo_id: int
    strength: int
    is_ai_generated: bool
    similarity_score: float | None
