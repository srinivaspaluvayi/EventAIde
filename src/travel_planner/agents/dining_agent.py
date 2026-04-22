from __future__ import annotations

from typing import Any

from travel_planner.models.schemas import FoodOption, TravelProfile
from travel_planner.providers.dining_provider import DiningProvider, NullDiningProvider
from travel_planner.utils.llm import SmallModelClient
from travel_planner.utils.logging import get_logger


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
    def __init__(
        self,
        llm: SmallModelClient,
        provider: DiningProvider | None = None,
        max_results: int = 30,
    ) -> None:
        self.llm = llm
        self.provider = provider or NullDiningProvider()
        self._max_results = max(5, min(int(max_results), 100))
        self._log = get_logger("travel_planner.dining")

    def run(self, profile: TravelProfile) -> list[FoodOption]:
        try:
            provider_results = self.provider.search_dining(profile)
            if provider_results:
                return self._dedupe(provider_results)[: self._max_results]
        except Exception as exc:
            self._log.error(
                "Dining: falling back to LLM after provider error (destination=%r).",
                profile.destination,
                exc_info=exc,
            )
        else:
            self._log.warning(
                "Dining: falling back to LLM — provider returned 0 results (destination=%r).",
                profile.destination,
            )
        prompt = (
            f"Destination: {profile.destination}\n"
            f"Interests: {', '.join(profile.interests)}\n"
            f"Travel style: {profile.travel_style}\n"
            f"Budget USD: {profile.budget_usd}\n"
            f"Return up to {self._max_results} distinct dining options in the JSON dining array."
        )
        fallback = [
            FoodOption(
                name="Local Market Food Hall",
                cuisine="Local mixed cuisine",
                price_level="$$",
                notes="[source:fallback:llm] Great for trying regional dishes in one place.",
            )
        ]
        try:
            tok = max(420, 200 + self._max_results * 45)
            parsed: dict[str, Any] = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=tok)
            dining = parsed.get("dining", [])
            result: list[FoodOption] = []
            for item in dining:
                if isinstance(item, dict):
                    result.append(
                        FoodOption(
                            name=str(item.get("name", "Popular local eatery")),
                            cuisine=str(item.get("cuisine", "Local cuisine")),
                            price_level=str(item.get("price_level", "$$")),
                            notes=self._with_fallback_source(
                                str(item.get("notes", "Check peak-hour wait times."))
                            ),
                        )
                    )
            deduped = self._dedupe(result)[: self._max_results]
            if deduped:
                self._log.info("Dining: LLM fallback returned %d option(s).", len(deduped))
                return deduped
            self._log.warning("Dining: LLM fallback returned no options; using static default list.")
            return fallback
        except Exception as exc:
            self._log.warning("Dining: LLM fallback failed; using static default list: %s", exc, exc_info=True)
            return fallback

    def _dedupe(self, items: list[FoodOption]) -> list[FoodOption]:
        out: list[FoodOption] = []
        seen: set[str] = set()
        for item in items:
            key = item.name.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _with_fallback_source(self, note: str) -> str:
        text = note.strip()
        if text.lower().startswith("[source:"):
            return text
        return f"[source:fallback:llm] {text}"

