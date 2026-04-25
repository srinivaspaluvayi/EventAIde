from __future__ import annotations

from travel_planner.models.schemas import PlaceOption, TravelProfile
from travel_planner.providers.places_provider import NullPlacesProvider, PlacesProvider
from travel_planner.utils.logging import get_logger


class PlacesDiscoveryAgent:
    def __init__(self, provider: PlacesProvider | None = None) -> None:
        self.provider = provider or NullPlacesProvider()
        self._log = get_logger("travel_planner.places")

    def run(self, profile: TravelProfile) -> list[PlaceOption]:
        try:
            rows = self.provider.search_places(profile)
            if rows:
                self._log.info("Places provider returned %d place(s).", len(rows))
                return rows
            self._log.warning("Places provider returned 0 rows for destination=%r.", profile.destination)
            return []
        except Exception as exc:
            self._log.error("Places provider error for destination=%r", profile.destination, exc_info=exc)
            return []

