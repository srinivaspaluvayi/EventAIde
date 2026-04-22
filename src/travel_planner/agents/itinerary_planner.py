from __future__ import annotations

from travel_planner.models.schemas import DestinationInfo, Itinerary, TravelProfile
from travel_planner.utils.llm import SmallModelClient
from travel_planner.utils.validators import trip_days


SYSTEM_PROMPT = """
You are Agent 3 (Itinerary Planner).
Create a day-by-day itinerary with morning/afternoon/evening.
Keep budget realistic and aligned with user interests.
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

    def run(self, profile: TravelProfile, destination_info: DestinationInfo) -> Itinerary:
        days = min(trip_days(profile.start_date, profile.end_date), 10)
        prompt = (
            f"Destination: {profile.destination}\n"
            f"Days: {days}\n"
            f"Budget USD: {profile.budget_usd}\n"
            f"Style: {profile.travel_style}\n"
            f"Interests: {', '.join(profile.interests)}\n"
            f"Highlights: {', '.join(destination_info.highlights)}\n"
            f"Weather: {destination_info.weather_summary}\n"
        )
        try:
            parsed = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=1200)
            return Itinerary(**parsed)
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

