from __future__ import annotations

from typing import Any

from travel_planner.models.schemas import HotelOption, TravelProfile
from travel_planner.providers.hotel_provider import HotelProvider, NullHotelProvider
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Hotel Search Agent.
Goal: produce realistic accommodation options aligned with destination, budget, group size, and trip style.

Requirements:
- Use all provided context fields; do not ignore user constraints.
- Return options with price-range diversity (budget/balanced/comfort when possible).
- Include neighborhood fit and practical highlights.
- Keep names/areas plausible and useful for planning.

Hard constraints:
- Do not invent booking URLs, exact room inventory, or guaranteed availability.
- Keep `price_range_usd` in readable nightly range format.

Output rules:
- Return JSON only, no markdown.
- Follow this exact schema:
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
                return provider_results
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
            return result or fallback
        except Exception:
            return fallback

