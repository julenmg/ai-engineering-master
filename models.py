from pydantic import BaseModel, field_validator


class EstimationRequest(BaseModel):
    transcription: str
    model: str | None = None  # override del modelo por petición

    @field_validator("transcription")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("transcription no puede estar vacía")
        return v


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int


class EstimationResponse(BaseModel):
    estimation: str
    model: str
    provider: str
    usage: TokenUsage
    latency_ms: int
