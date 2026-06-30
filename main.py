from fastapi import FastAPI, HTTPException, Depends
from models import EstimationRequest, EstimationResponse, TokenUsage
from llm_service import generate_estimation
from config import get_settings, Settings

app = FastAPI(title="Meeting Estimator API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/estimate", response_model=EstimationResponse)
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
