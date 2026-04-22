from __future__ import annotations

from typing import Dict, List

from travel_planner.models.schemas import Itinerary


def itinerary_cost_table(itinerary: Itinerary) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for day in itinerary.days:
        rows.append({"day": day.day, "cost_usd": round(day.day_total_usd, 2)})
    return rows

