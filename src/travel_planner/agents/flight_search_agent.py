from __future__ import annotations

from typing import Any

from travel_planner.models.schemas import FlightOption, TravelProfile
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Flight Search Agent.
Mission: provide practical flight planning options for itinerary budgeting.

Workflow:
1) Infer likely route pattern from user destination and trip dates.
2) Provide 1-3 realistic options with distinct tradeoffs:
- best value
- convenience (fewer stops / better timing)
- balanced option
3) Include concise notes on booking strategy and constraints.

Reliability and grounding rules:
- do not invent exact flight numbers, real-time prices, or guaranteed schedules
- represent routes at practical planning level (origin hub -> destination)
- keep costs plausible and internally consistent with trip budget

Output policy:
- JSON only, no prose outside schema
- concise notes focused on decision-making

Return strict JSON shape:
{
  "flights": [
    {"route":"...","airline":"...","estimated_cost_usd": 0,"notes":"..."}
  ]
}
"""


class FlightSearchAgent:
    def __init__(self, llm: SmallModelClient) -> None:
        self.llm = llm

    def run(self, profile: TravelProfile) -> list[FlightOption]:
        prompt = (
            f"Destination: {profile.destination}\n"
            f"Dates: {profile.start_date} to {profile.end_date}\n"
            f"Budget USD: {profile.budget_usd}\n"
            f"Style: {profile.travel_style}"
        )
        fallback = [
            FlightOption(
                route=f"Major hub -> {profile.destination}",
                airline="Best-value carrier",
                estimated_cost_usd=max(profile.budget_usd * 0.22, 180),
                notes="Book 4-8 weeks early for better fares.",
            )
        ]
        try:
            parsed: dict[str, Any] = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=420)
            flights = parsed.get("flights", [])
            result: list[FlightOption] = []
            for item in flights:
                if isinstance(item, dict):
                    result.append(
                        FlightOption(
                            route=str(item.get("route", f"Major hub -> {profile.destination}")),
                            airline=str(item.get("airline", "Recommended carrier")),
                            estimated_cost_usd=float(item.get("estimated_cost_usd", max(profile.budget_usd * 0.22, 180))),
                            notes=str(item.get("notes", "Compare baggage policies before booking.")),
                        )
                    )
            return result[:3] or fallback
        except Exception:
            return fallback

