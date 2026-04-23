from __future__ import annotations

from typing import Any

from travel_planner.models.schemas import FlightOption, TravelProfile
from travel_planner.providers.flight_provider import FlightProvider, NullFlightProvider
from travel_planner.utils.llm import SmallModelClient
from travel_planner.utils.logging import get_logger


SYSTEM_PROMPT = """
You are Flight Search Agent.
Mission: provide practical flight planning options for itinerary budgeting.

Workflow:
1) Infer likely route pattern from user destination and trip dates.
2) Provide several realistic options (as many as requested in the user message, up to the stated cap) with distinct tradeoffs:
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
    def __init__(
        self,
        llm: SmallModelClient,
        provider: FlightProvider | None = None,
        max_results: int = 12,
    ) -> None:
        self.llm = llm
        self.provider = provider or NullFlightProvider()
        self._max_results = max(5, min(int(max_results), 25))
        self._log = get_logger("travel_planner.flights")

    def run(self, profile: TravelProfile) -> list[FlightOption]:
        try:
            provider_rows = self.provider.search_flights(profile)
            if provider_rows:
                return self._dedupe(provider_rows)[: self._max_results]
        except Exception as exc:
            self._log.error(
                "Flight provider error; using LLM fallback (destination=%r).",
                profile.destination,
                exc_info=exc,
            )
        else:
            # ``NullFlightProvider`` always returns []; that is not a failed SerpAPI request.
            if isinstance(self.provider, NullFlightProvider):
                self._log.debug(
                    "Flight live provider disabled; LLM estimates only (destination=%r).",
                    profile.destination,
                )
            else:
                self._log.warning(
                    "SerpAPI Google Flights returned no bundles for destination=%r "
                    "(check FLIGHT_DEPARTURE_ID / FLIGHT_ARRIVAL_ID or a 3-letter IATA in destination, and dates). "
                    "Using LLM fallback.",
                    profile.destination,
                )

        prompt = (
            f"Destination: {profile.destination}\n"
            f"Dates: {profile.start_date} to {profile.end_date}\n"
            f"Budget USD: {profile.budget_usd}\n"
            f"Style: {profile.travel_style}\n"
            f"Return up to {self._max_results} distinct flight options in the JSON flights array."
        )
        fallback = [
            FlightOption(
                route=f"Major hub -> {profile.destination}",
                airline="Best-value carrier",
                estimated_cost_usd=max(profile.budget_usd * 0.22, 180),
                notes="[source:fallback:llm] Book 4-8 weeks early for better fares.",
            )
        ]
        try:
            tok = max(420, 180 + self._max_results * 55)
            parsed: dict[str, Any] = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=tok)
            flights = parsed.get("flights", [])
            result: list[FlightOption] = []
            for item in flights:
                if isinstance(item, dict):
                    result.append(
                        FlightOption(
                            route=str(item.get("route", f"Major hub -> {profile.destination}")),
                            airline=str(item.get("airline", "Recommended carrier")),
                            estimated_cost_usd=float(
                                item.get("estimated_cost_usd", max(profile.budget_usd * 0.22, 180))
                            ),
                            notes=self._with_fallback_source(
                                str(item.get("notes", "Compare baggage policies before booking."))
                            ),
                        )
                    )
            return self._dedupe(result)[: self._max_results] or fallback
        except Exception as exc:
            self._log.warning("Flight LLM fallback failed: %s", exc, exc_info=True)
            return fallback

    def _dedupe(self, items: list[FlightOption]) -> list[FlightOption]:
        out: list[FlightOption] = []
        seen: set[str] = set()
        for item in items:
            key = item.route.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    @staticmethod
    def _with_fallback_source(note: str) -> str:
        text = note.strip()
        if text.lower().startswith("[source:"):
            return text
        return f"[source:fallback:llm] {text}"
