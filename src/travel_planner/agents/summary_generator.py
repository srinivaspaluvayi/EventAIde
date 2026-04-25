from __future__ import annotations

from travel_planner.models.schemas import DestinationInfo, FlightOption, Itinerary, Logistics, TravelProfile
from travel_planner.utils.html_renderer import render_html


class SummaryGeneratorAgent:
    def run(
        self,
        profile: TravelProfile,
        destination_info: DestinationInfo,
        itinerary: Itinerary,
        logistics: Logistics,
        flights: list[FlightOption] | None = None,
    ) -> str:
        return render_html(profile, destination_info, itinerary, logistics, flights=flights or [])

