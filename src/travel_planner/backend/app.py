from __future__ import annotations

from fastapi import FastAPI, HTTPException

from travel_planner.backend.schemas import ErrorResponse, HealthResponse, PlanRequest, PlanResponse
from travel_planner.backend.service import PlanService


app = FastAPI(title="TripForge API", version="1.0.0")
service = PlanService()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="tripforge-api")


@app.post("/v1/plan", response_model=PlanResponse, responses={500: {"model": ErrorResponse}})
def generate_plan(payload: PlanRequest) -> PlanResponse:
    try:
        plan = service.generate_plan(payload.user_input)
        return PlanResponse(plan=plan)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {exc}") from exc


def run() -> None:
    import uvicorn

    uvicorn.run("travel_planner.backend.app:app", host="0.0.0.0", port=8000, reload=False)

