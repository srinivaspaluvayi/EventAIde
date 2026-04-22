from __future__ import annotations

from travel_planner.models.schemas import BudgetPlan, DestinationInfo, FoodOption, FlightOption, HotelOption, Itinerary, TravelProfile
from travel_planner.utils.llm import SmallModelClient
from travel_planner.utils.validators import trip_days


SYSTEM_PROMPT = """
You are Agent 3 (Itinerary Planner).
Create a day-by-day itinerary with morning/afternoon/evening.
Keep budget realistic and aligned with user interests.
Ground every recommendation in provided context only.
Do not invent specific origin cities, flight numbers, hotel names, or restaurant names
unless they are explicitly present in the given context fields.
If a specific detail is unknown, use neutral wording (e.g., "arrival and local transfer",
"local lunch spot", "city-center stay").
Planning quality rules:
- keep day flow realistic (effort balance and travel practicality)
- avoid overpacking each day
- include variety across cultural/food/leisure interests
- keep per-slot costs plausible relative to total budget
Consistency rules:
- day_total_usd should reflect slot-level costs
- estimated_total_usd should align with sum of all days
Output policy:
- JSON only
- no markdown
Return strict JSON:
{
  "trip_title": "...",
  "days": [
    {
      "day": 1,
      "morning": {"slot":"morning","title":"...","details":"...","estimated_cost_usd": 0},
      "afternoon": {"slot":"afternoon","title":"...","details":"...","estimated_cost_usd": 0},
      "evening": {"slot":"evening","title":"...","details":"...","estimated_cost_usd": 0},
      "day_total_usd": 0
    }
  ],
  "estimated_total_usd": 0
}
"""


class ItineraryPlannerAgent:
    def __init__(self, llm: SmallModelClient) -> None:
        self.llm = llm

    def run(
        self,
        profile: TravelProfile,
        destination_info: DestinationInfo,
        flights: list[FlightOption] | None = None,
        hotels: list[HotelOption] | None = None,
        dining: list[FoodOption] | None = None,
        budget_plan: BudgetPlan | None = None,
    ) -> Itinerary:
        days = min(trip_days(profile.start_date, profile.end_date), 10)
        flight_hint = flights[0].route if flights else "Best-route option"
        hotel_hint = hotels[0].name if hotels else "Central stay option"
        dining_hint = dining[0].name if dining else "Local food hall"
        budget_hint = budget_plan.total_planned_usd if budget_plan else profile.budget_usd
        prompt = (
            f"Destination: {profile.destination}\n"
            f"Days: {days}\n"
            f"Budget USD: {profile.budget_usd}\n"
            f"Style: {profile.travel_style}\n"
            f"Interests: {', '.join(profile.interests)}\n"
            f"Highlights: {', '.join(destination_info.highlights)}\n"
            f"Weather: {destination_info.weather_summary}\n"
            f"Flight context: {flight_hint}\n"
            f"Hotel context: {hotel_hint}\n"
            f"Dining context: {dining_hint}\n"
            f"Budget target total: {budget_hint}\n"
        )
        try:
            parsed = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=1200)
            itinerary = Itinerary(**parsed)
            return self._sanitize_itinerary(itinerary)
        except Exception:
            days_payload = []
            daily_budget = profile.budget_usd / max(days, 1)
            for day in range(1, days + 1):
                morning_cost = round(daily_budget * 0.25, 2)
                afternoon_cost = round(daily_budget * 0.45, 2)
                evening_cost = round(daily_budget * 0.30, 2)
                total = round(morning_cost + afternoon_cost + evening_cost, 2)
                days_payload.append(
                    {
                        "day": day,
                        "morning": {
                            "slot": "morning",
                            "title": "Local breakfast and walking tour",
                            "details": "Start in a central neighborhood and visit nearby highlights.",
                            "estimated_cost_usd": morning_cost,
                        },
                        "afternoon": {
                            "slot": "afternoon",
                            "title": "Main activity block",
                            "details": f"Focus on {profile.interests[0] if profile.interests else 'popular attractions'}.",
                            "estimated_cost_usd": afternoon_cost,
                        },
                        "evening": {
                            "slot": "evening",
                            "title": "Dinner and relaxed exploration",
                            "details": "End with local cuisine and a low-intensity activity.",
                            "estimated_cost_usd": evening_cost,
                        },
                        "day_total_usd": total,
                    }
                )
            total_est = round(sum(day["day_total_usd"] for day in days_payload), 2)
            return Itinerary(trip_title=f"{profile.destination} Trip Plan", days=days_payload, estimated_total_usd=total_est)

    def _sanitize_itinerary(self, itinerary: Itinerary) -> Itinerary:
        # Remove common hallucinated specificity when not grounded.
        blocked_tokens = [
            "los angeles",
            "new york city",
            "katz",
            "check-in at",
            "flight number",
        ]

        def _clean_text(value: str) -> str:
            text = value.strip()
            lower = text.lower()
            if any(token in lower for token in blocked_tokens):
                return "Planned activity based on your preferences and local availability."
            return text

        for day in itinerary.days:
            day.morning.title = _clean_text(day.morning.title)
            day.morning.details = _clean_text(day.morning.details)
            day.afternoon.title = _clean_text(day.afternoon.title)
            day.afternoon.details = _clean_text(day.afternoon.details)
            day.evening.title = _clean_text(day.evening.title)
            day.evening.details = _clean_text(day.evening.details)
        return itinerary

