from __future__ import annotations

from typing import Any

from travel_planner.models.schemas import BudgetPlan, FoodOption, FlightOption, HotelOption, TravelProfile
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Budget Agent.
Mission: produce a realistic, defensible trip budget split with optimization advice.

Workflow:
1) Reconcile budget target against known cost drivers (flight/stay/food/activities).
2) Allocate budget into clear categories with realistic proportions.
3) Keep total near user target and provide optimization tips if over budget.

Hard rules:
- all category values must be non-negative numbers
- total_planned_usd must equal category sum (within rounding tolerance)
- optimization tips must be concrete and actionable
- avoid vague tips like "spend less"

Output policy:
- JSON only
- no markdown or commentary

Return strict JSON shape:
{
  "transportation_usd": 0,
  "stay_usd": 0,
  "food_usd": 0,
  "activities_usd": 0,
  "buffer_usd": 0,
  "total_planned_usd": 0,
  "optimization_tips": ["..."]
}
"""


class BudgetOptimizerAgent:
    def __init__(self, llm: SmallModelClient) -> None:
        self.llm = llm

    def run(
        self,
        profile: TravelProfile,
        flights: list[FlightOption],
        hotels: list[HotelOption],
        dining: list[FoodOption],
    ) -> BudgetPlan:
        flight_cost = sum(item.estimated_cost_usd for item in flights)
        stay_cost = profile.budget_usd * 0.35
        food_cost = profile.budget_usd * 0.2
        activities = profile.budget_usd * 0.18
        buffer = profile.budget_usd * 0.08
        fallback = BudgetPlan(
            transportation_usd=round(flight_cost, 2),
            stay_usd=round(stay_cost, 2),
            food_usd=round(food_cost, 2),
            activities_usd=round(activities, 2),
            buffer_usd=round(buffer, 2),
            total_planned_usd=round(flight_cost + stay_cost + food_cost + activities + buffer, 2),
            optimization_tips=[
                "Book flights and stays early to reduce peak pricing.",
                "Use city transport passes for daily mobility.",
            ],
        )
        prompt = (
            f"Budget target: {profile.budget_usd}\n"
            f"Flight estimates: {flight_cost}\n"
            f"Hotel candidates: {', '.join(h.name for h in hotels[:3])}\n"
            f"Dining candidates: {', '.join(d.name for d in dining[:3])}\n"
        )
        try:
            parsed: dict[str, Any] = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=420)
            return BudgetPlan(
                transportation_usd=float(parsed.get("transportation_usd", fallback.transportation_usd)),
                stay_usd=float(parsed.get("stay_usd", fallback.stay_usd)),
                food_usd=float(parsed.get("food_usd", fallback.food_usd)),
                activities_usd=float(parsed.get("activities_usd", fallback.activities_usd)),
                buffer_usd=float(parsed.get("buffer_usd", fallback.buffer_usd)),
                total_planned_usd=float(parsed.get("total_planned_usd", fallback.total_planned_usd)),
                optimization_tips=[
                    str(x).strip()
                    for x in parsed.get("optimization_tips", fallback.optimization_tips)
                    if str(x).strip()
                ][:5],
            )
        except Exception:
            return fallback

