from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol

from travel_planner.models.schemas import PlaceOption, TravelProfile


class PlacesProvider(Protocol):
    def search_places(self, profile: TravelProfile) -> List[PlaceOption]:
        ...


@dataclass
class NullPlacesProvider:
    def search_places(self, profile: TravelProfile) -> List[PlaceOption]:
        return []

