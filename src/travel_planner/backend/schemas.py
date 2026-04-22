from __future__ import annotations

from pydantic import BaseModel, Field

from travel_planner.models.schemas import FinalPlan


class PlanRequest(BaseModel):
    user_input: str = Field(..., min_length=8)


class PlanResponse(BaseModel):
    plan: FinalPlan


class HealthResponse(BaseModel):
    status: str
    service: str


class ErrorResponse(BaseModel):
    detail: str

