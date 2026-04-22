from __future__ import annotations

from typing import List

from travel_planner.models.schemas import DestinationInfo, TravelProfile
from travel_planner.tools.search_tool import web_search
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Agent 2 (Destination Research).
Mission: synthesize destination intelligence from provided web snippets into practical trip guidance.

Workflow:
1) Extract strongest recurring signals from snippets.
2) Prioritize information that affects traveler decisions:
- top attractions
- best areas to stay
- local operational tips
- visa/travel compliance basics
- weather and seasonality implications
3) Keep outputs concrete and useful for itinerary planning.

Grounding rules:
- use snippet evidence; do not fabricate specific facts not supported by context
- when uncertain, use cautious wording and practical verification advice
- keep lists non-redundant

Output policy:
- JSON only
- no markdown
- return exactly these keys:
highlights, best_areas_to_stay, local_tips, visa_requirements, weather_summary, sources
"""


class DestinationResearchAgent:
    def __init__(self, llm: SmallModelClient, max_search_results: int = 6) -> None:
        self.llm = llm
        self.max_search_results = max_search_results

    def run(self, profile: TravelProfile) -> DestinationInfo:
        queries = [
            f"{profile.destination} top attractions",
            f"best areas to stay in {profile.destination}",
            f"{profile.destination} visa requirements for tourists",
            f"{profile.destination} weather by month",
        ]
        snippets: List[str] = []
        for query in queries:
            snippets.extend(web_search(query, max_results=max(3, self.max_search_results // 2)))
        context = "\n".join(snippets[: self.max_search_results])

        fallback = {
            "highlights": [f"Explore central landmarks in {profile.destination}"],
            "best_areas_to_stay": ["City center"],
            "local_tips": ["Carry a local transport card.", "Book popular attractions early."],
            "visa_requirements": "Check your nationality-specific government advisory before travel.",
            "weather_summary": "Expect typical seasonal variation; verify forecast one week before departure.",
            "sources": snippets[:3],
        }
        prompt = f"Destination: {profile.destination}\nTravel dates: {profile.start_date} to {profile.end_date}\nWeb snippets:\n{context}"
        try:
            parsed = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=560)
        except Exception:
            parsed = fallback
        return DestinationInfo(**{**fallback, **parsed})

