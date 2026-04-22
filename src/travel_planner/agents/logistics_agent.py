from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from travel_planner.models.schemas import DestinationInfo, Itinerary, Logistics, TravelProfile
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Agent 4 (Logistics Agent).
Generate practical logistics in strict JSON with keys:
accommodation_options, local_transport, packing_tips
"""


class LogisticsAgent:
    def __init__(self, llm: SmallModelClient) -> None:
        self.llm = llm

    def _debug_log(self, run_id: str, hypothesis_id: str, location: str, message: str, data: Dict[str, Any]) -> None:
        payload = {
            "sessionId": "39ed9e",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        log_path = Path("/Volumes/External/Drive_C/EventAIde/.cursor/debug-39ed9e.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def run(self, profile: TravelProfile, destination_info: DestinationInfo, itinerary: Itinerary) -> Logistics:
        # region agent log
        self._debug_log(
            run_id="run1",
            hypothesis_id="H1",
            location="logistics_agent.py:run:start",
            message="LogisticsAgent run entry",
            data={
                "destination": profile.destination,
                "group_size": profile.group_size,
                "days_count": len(itinerary.days),
            },
        )
        # endregion
        prompt = (
            f"Destination: {profile.destination}\n"
            f"Budget USD: {profile.budget_usd}\n"
            f"Group size: {profile.group_size}\n"
            f"Weather: {destination_info.weather_summary}\n"
            f"Days planned: {len(itinerary.days)}"
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
            # region agent log
            self._debug_log(
                run_id="run1",
                hypothesis_id="H2",
                location="logistics_agent.py:run:parsed",
                message="Raw parsed logistics payload shape",
                data={
                    "parsed_type": type(parsed).__name__,
                    "keys": list(parsed.keys()) if isinstance(parsed, dict) else [],
                    "accommodation_options_type": type(parsed.get("accommodation_options")).__name__
                    if isinstance(parsed, dict)
                    else "unknown",
                    "local_transport_type": type(parsed.get("local_transport")).__name__ if isinstance(parsed, dict) else "unknown",
                    "packing_tips_type": type(parsed.get("packing_tips")).__name__ if isinstance(parsed, dict) else "unknown",
                },
            )
            # endregion
        except Exception:
            parsed = fallback
            # region agent log
            self._debug_log(
                run_id="run1",
                hypothesis_id="H4",
                location="logistics_agent.py:run:llm_exception",
                message="LLM call failed; fallback used",
                data={"fallback_used": True},
            )
            # endregion
        merged = {**fallback, **parsed} if isinstance(parsed, dict) else fallback
        merged = self._normalize_payload(merged, fallback)
        # region agent log
        self._debug_log(
            run_id="run1",
            hypothesis_id="H3",
            location="logistics_agent.py:run:pre_validate",
            message="Merged payload before Logistics validation",
            data={
                "accommodation_options_type": type(merged.get("accommodation_options")).__name__,
                "local_transport_type": type(merged.get("local_transport")).__name__,
                "packing_tips_type": type(merged.get("packing_tips")).__name__,
                "accommodation_item0_type": type(merged.get("accommodation_options")[0]).__name__
                if isinstance(merged.get("accommodation_options"), list) and merged.get("accommodation_options")
                else "none",
            },
        )
        # endregion
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

