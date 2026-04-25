from __future__ import annotations

from typing import Any, List

from travel_planner.models.schemas import DestinationInfo, TravelProfile
from travel_planner.tools.search_tool import web_search
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Agent 2 (Destination Research).
Goal: convert provided web snippets into concise, practical destination guidance.

What to produce:
- `highlights`: strongest destination draws for this trip
- `best_areas_to_stay`: neighborhood recommendations as plain strings
- `local_tips`: actionable on-the-ground tips
- `visa_requirements`: practical compliance note with cautious wording
- `weather_summary`: seasonal implications relevant to the trip dates
- `sources`: short snippet references used for grounding

Grounding constraints:
- Use only information supported by the provided snippets.
- Do not fabricate precise facts, policies, or venue-specific claims.
- If uncertain, state uncertainty briefly and suggest verification.
- Keep output non-redundant and decision-oriented.

Schema constraints:
- Return JSON only, no markdown.
- Return exactly these keys:
  highlights, best_areas_to_stay, local_tips, visa_requirements, weather_summary, sources
- `best_areas_to_stay` MUST be an array of strings only (no objects).
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
        merged = {**fallback, **parsed}
        merged["highlights"] = self._normalize_text_list(merged.get("highlights"), fallback["highlights"])
        merged["best_areas_to_stay"] = self._normalize_areas_list(
            merged.get("best_areas_to_stay"), fallback["best_areas_to_stay"]
        )
        merged["local_tips"] = self._normalize_text_list(merged.get("local_tips"), fallback["local_tips"])
        merged["sources"] = self._normalize_text_list(merged.get("sources"), fallback["sources"])
        merged["visa_requirements"] = self._normalize_text(
            merged.get("visa_requirements"), fallback["visa_requirements"]
        )
        merged["weather_summary"] = self._normalize_text(merged.get("weather_summary"), fallback["weather_summary"])
        return DestinationInfo(**merged)

    def _normalize_text(self, value: Any, fallback: str) -> str:
        if isinstance(value, str):
            text = value.strip()
            return text or fallback
        return fallback

    def _normalize_text_list(self, value: Any, fallback: List[str]) -> List[str]:
        if not isinstance(value, list):
            return fallback
        out: List[str] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    out.append(text)
        return out or fallback

    def _normalize_areas_list(self, value: Any, fallback: List[str]) -> List[str]:
        """Accept either strings or {neighborhood, why}-style dicts from the LLM."""
        if not isinstance(value, list):
            return fallback
        out: List[str] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    out.append(text)
                continue
            if isinstance(item, dict):
                neighborhood = str(item.get("neighborhood", "")).strip()
                reason = str(item.get("why", "")).strip() or str(item.get("reason", "")).strip()
                if neighborhood and reason:
                    out.append(f"{neighborhood}: {reason}")
                elif neighborhood:
                    out.append(neighborhood)
                elif reason:
                    out.append(reason)
        return out or fallback

