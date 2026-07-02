from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.schemas.estimation import (
    EstimationRequest,
    EstimationResponse,
    GenerationOptions,
    StructureCheck,
    TokenUsage,
)
from app.services.evaluation import evaluate_estimation_structure
from app.services.llm_service import generate_estimation

router = APIRouter()


@router.post("/estimate", response_model=EstimationResponse)
async def estimate(
    body: EstimationRequest,
    settings: Settings = Depends(get_settings),
) -> EstimationResponse:
    opts = GenerationOptions(
        transcription=body.transcription,
        preprocessing=body.preprocessing,
        example_format=body.example_format,
        num_examples=body.num_examples,
        model=body.model or settings.llm_model,
        max_tokens=body.max_tokens,
        thinking_budget=body.thinking_budget,
        evaluate=body.evaluate,
    )

    try:
        result = await generate_estimation(opts, settings)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    validation: StructureCheck | None = None
    if body.evaluate:
        validation = evaluate_estimation_structure(result["estimation"], result["finish_reason"])

    return EstimationResponse(
        estimation=result["estimation"],
        model=result["model"],
        provider=result["provider"],
        finish_reason=result["finish_reason"],
        preprocessing=result["preprocessing"],
        extracted_requirements=result.get("extracted_requirements"),
        latency_ms=result["latency_ms"],
        usage=TokenUsage(**result["usage"]),
        validation=validation,
    )
