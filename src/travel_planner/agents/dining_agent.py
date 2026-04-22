from __future__ import annotations

from typing import Any

from travel_planner.models.schemas import FoodOption, TravelProfile
from travel_planner.providers.dining_provider import DiningProvider, NullDiningProvider
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Dining Agent.
Mission: recommend high-quality dining options that match traveler intent and budget.

Workflow:
1) Infer dining profile from interests, travel style, and budget.
2) Return a diverse mix:
- one local signature experience
- one reliable crowd-pleaser
- one flexible/value option
3) Keep entries practical for itinerary insertion.

Reliability rules:
- do not invent reservation confirmations or exact table availability
- avoid niche-only picks unless strongly implied by interests
- notes must explain fit (ambiance, value, cuisine uniqueness)

Output policy:
- JSON only
- no markdown
- concise, decision-friendly descriptions

Return strict JSON shape:
{
  "dining": [
    {"name":"...","cuisine":"...","price_level":"$|$$|$$$","notes":"..."}
  ]
}
"""


class DiningAgent:
    def __init__(self, llm: SmallModelClient, provider: DiningProvider | None = None) -> None:
        self.llm = llm
        self.provider = provider or NullDiningProvider()

    def run(self, profile: TravelProfile) -> list[FoodOption]:
        try:
            provider_results = self.provider.search_dining(profile)
            if provider_results:
                return provider_results[:5]
        except Exception:
            pass

        prompt = (
            f"Destination: {profile.destination}\n"
            f"Interests: {', '.join(profile.interests)}\n"
            f"Travel style: {profile.travel_style}\n"
            f"Budget USD: {profile.budget_usd}"
        )
        fallback = [
            FoodOption(
                name="Local Market Food Hall",
                cuisine="Local mixed cuisine",
                price_level="$$",
                notes="Great for trying regional dishes in one place.",
            )
        ]
        try:
            parsed: dict[str, Any] = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=420)
            dining = parsed.get("dining", [])
            result: list[FoodOption] = []
            for item in dining:
                if isinstance(item, dict):
                    result.append(
                        FoodOption(
                            name=str(item.get("name", "Popular local eatery")),
                            cuisine=str(item.get("cuisine", "Local cuisine")),
                            price_level=str(item.get("price_level", "$$")),
                            notes=str(item.get("notes", "Check peak-hour wait times.")),
                        )
                    )
            return result[:5] or fallback
        except Exception:
            return fallback

