from fastapi import FastAPI
from app.routers import estimations

app = FastAPI(title="Meeting Estimator API", version="0.1.0")

app.include_router(estimations.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "healthy"}
