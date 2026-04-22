from __future__ import annotations

from travel_planner.config.settings import Settings
from travel_planner.models.schemas import FinalPlan
from travel_planner.orchestration.pipeline import TravelPlannerPipeline


class PlanService:
    def __init__(self) -> None:
        settings = Settings.from_env()
        self.pipeline = TravelPlannerPipeline(settings=settings)

    def generate_plan(self, user_input: str) -> FinalPlan:
        return self.pipeline.run(user_input=user_input)

