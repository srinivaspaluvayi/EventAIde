from __future__ import annotations

from typing import Any, Dict

from travel_planner.models.schemas import DestinationInfo, FlightOption, HotelOption, Itinerary, Logistics, TravelProfile
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Agent 4 (Logistics Agent).
Goal: turn trip context into actionable logistics that travelers can execute.

Requirements:
- Use all provided context: profile, weather, itinerary shape, hotels, flights.
- Prioritize practical reliability over novelty.
- Produce concise, concrete recommendations (not generic filler).
- Avoid duplicates and near-duplicates.

Output rules:
- Return JSON only, no markdown, no extra keys.
- Return exactly these keys:
  accommodation_options, local_transport, packing_tips
"""


class LogisticsAgent:
    def __init__(self, llm: SmallModelClient) -> None:
        self.llm = llm

    def run(
        self,
        profile: TravelProfile,
        destination_info: DestinationInfo,
        itinerary: Itinerary,
        hotels: list[HotelOption] | None = None,
        flights: list[FlightOption] | None = None,
    ) -> Logistics:
        prompt = (
            f"Destination: {profile.destination}\n"
            f"Budget USD: {profile.budget_usd}\n"
            f"Group size: {profile.group_size}\n"
            f"Weather: {destination_info.weather_summary}\n"
            f"Days planned: {len(itinerary.days)}\n"
            f"Hotel suggestions: {', '.join(h.name for h in (hotels or [])[:3])}\n"
            f"Flight notes: {', '.join(f.notes for f in (flights or [])[:2])}"
        )
        fallback = {
            "accommodation_options": [
                "Budget hotel: $40-$70/night",
                "Mid-range hotel: $80-$140/night",
                "Boutique stay: $150-$220/night",
            ],
            "local_transport": [
                "Use public transport day passes for city travel.",
                "Use ride-hailing only for late-night transfers.",
            ],
            "packing_tips": [
                "Pack one light rain layer.",
                "Carry comfortable walking shoes.",
                "Bring a compact power bank.",
            ],
        }
        try:
            parsed = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=420)
        except Exception:
            parsed = fallback
        merged = {**fallback, **parsed} if isinstance(parsed, dict) else fallback
        merged = self._normalize_payload(merged, fallback)
        if hotels:
            merged["accommodation_options"] = [
                f"{h.name} ({h.area}) - {h.price_range_usd}" for h in hotels[:3]
            ] + merged["accommodation_options"]
        if flights:
            merged["local_transport"] = [f"Flight note: {f.notes}" for f in flights[:2]] + merged["local_transport"]
        return Logistics(**merged)

    def _normalize_payload(self, merged: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {**fallback, **merged}
        normalized["accommodation_options"] = self._to_string_list(normalized.get("accommodation_options"))
        normalized["local_transport"] = self._to_string_list(normalized.get("local_transport"))
        normalized["packing_tips"] = self._to_string_list(normalized.get("packing_tips"))

        if not normalized["accommodation_options"]:
            normalized["accommodation_options"] = fallback["accommodation_options"]
        if not normalized["local_transport"]:
            normalized["local_transport"] = fallback["local_transport"]
        if not normalized["packing_tips"]:
            normalized["packing_tips"] = fallback["packing_tips"]
        return normalized

    def _to_string_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            items: list[str] = []
            for entry in value:
                if isinstance(entry, str) and entry.strip():
                    items.append(entry.strip())
                elif isinstance(entry, dict):
                    parts = [str(v).strip() for v in entry.values() if isinstance(v, (str, int, float)) and str(v).strip()]
                    if parts:
                        items.append(" | ".join(parts[:3]))
            return items[:8]

        if isinstance(value, dict):
            if "options" in value and isinstance(value["options"], list):
                return self._to_string_list(value["options"])
            parts = [f"{k}: {v}" for k, v in value.items() if isinstance(v, (str, int, float)) and str(v).strip()]
            return parts[:8]

        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

