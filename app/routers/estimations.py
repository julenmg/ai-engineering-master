from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from app.services.llm_service import generate_estimation
from app.config import get_settings, Settings

router = APIRouter()


class EstimationRequest(BaseModel):
    transcription: str
    model: str | None = None

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


@router.post("/estimate", response_model=EstimationResponse)
async def estimate(
    body: EstimationRequest,
    settings: Settings = Depends(get_settings),
) -> EstimationResponse:
    try:
        result = await generate_estimation(body.transcription, settings, body.model)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    return EstimationResponse(
        estimation=result["estimation"],
        model=result["model"],
        provider=result["provider"],
        usage=TokenUsage(**result["usage"]),
        latency_ms=result["latency_ms"],
    )
