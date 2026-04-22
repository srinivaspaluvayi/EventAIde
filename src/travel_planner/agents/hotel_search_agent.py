from __future__ import annotations

from typing import Any

from travel_planner.models.schemas import HotelOption, TravelProfile
from travel_planner.providers.hotel_provider import HotelProvider, NullHotelProvider
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Hotel Search Agent.
Mission: return realistic accommodation options aligned to budget, group type, and trip style.

Workflow:
1) Parse constraints:
- destination, trip style, group size, budget level
- likely location preferences (walkability, transit, family-friendliness)
2) Build 3-5 options with range diversity:
- budget, balanced, and comfort tiers when possible
3) Keep recommendations practical:
- avoid luxury-only or generic-only lists
- include neighborhood context and why it fits
4) Reliability rules:
- do not invent booking links or exact room inventory
- use realistic nightly range strings and concise highlights

Output policy:
- return JSON only
- keep fields concise and useful for itinerary planning
- no markdown

Return strict JSON shape:
{
  "hotels": [
    {"name":"...","area":"...","price_range_usd":"...","highlights":["..."]}
  ]
}
"""


class HotelSearchAgent:
    def __init__(self, llm: SmallModelClient, provider: HotelProvider | None = None) -> None:
        self.llm = llm
        self.provider = provider or NullHotelProvider()

    def run(self, profile: TravelProfile) -> list[HotelOption]:
        try:
            provider_results = self.provider.search_hotels(profile)
            if provider_results:
                return provider_results[:5]
        except Exception:
            pass

        prompt = (
            f"Destination: {profile.destination}\n"
            f"Group size: {profile.group_size}\n"
            f"Budget USD: {profile.budget_usd}\n"
            f"Style: {profile.travel_style}"
        )
        fallback = [
            HotelOption(
                name=f"{profile.destination} Central Stay",
                area="City center",
                price_range_usd="$80-$140/night",
                highlights=["Good transit access", "Walkable neighborhood"],
            )
        ]
        try:
            parsed: dict[str, Any] = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=450)
            hotels = parsed.get("hotels", [])
            result: list[HotelOption] = []
            for item in hotels:
                if isinstance(item, dict):
                    raw_highlights = item.get("highlights", [])
                    highlights = [str(x).strip() for x in raw_highlights if str(x).strip()] if isinstance(raw_highlights, list) else []
                    result.append(
                        HotelOption(
                            name=str(item.get("name", f"{profile.destination} Stay Option")),
                            area=str(item.get("area", "Central area")),
                            price_range_usd=str(item.get("price_range_usd", "$70-$130/night")),
                            highlights=highlights[:4],
                        )
                    )
            return result[:4] or fallback
        except Exception:
            return fallback

