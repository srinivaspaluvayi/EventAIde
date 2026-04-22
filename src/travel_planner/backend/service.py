from __future__ import annotations

from travel_planner.config.settings import Settings
from travel_planner.models.schemas import FinalPlan
from travel_planner.orchestration.pipeline import TravelPlannerPipeline


class PlanService:
    """Builds a fresh pipeline per request so ``.env`` changes (e.g. ``GEOAPIFY_API_KEY``) apply without restarting."""

    def generate_plan(self, user_input: str) -> FinalPlan:
        settings = Settings.from_env()
        return TravelPlannerPipeline(settings=settings).run(user_input=user_input)

