from __future__ import annotations

from travel_planner.models.schemas import ShowOption, TravelProfile
from travel_planner.providers.show_provider import NullShowProvider, ShowProvider
from travel_planner.utils.logging import get_logger


class ShowDiscoveryAgent:
    def __init__(self, provider: ShowProvider | None = None) -> None:
        self.provider = provider or NullShowProvider()
        self._log = get_logger("travel_planner.shows")

    def run(self, profile: TravelProfile) -> list[ShowOption]:
        try:
            rows = self.provider.search_shows(profile)
            if rows:
                self._log.info("Show provider returned %d event(s).", len(rows))
                return rows
            self._log.warning("Show provider returned 0 events for destination=%r.", profile.destination)
            return []
        except Exception as exc:
            self._log.error("Show provider error for destination=%r", profile.destination, exc_info=exc)
            return []

