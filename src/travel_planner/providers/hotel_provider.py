from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol

from travel_planner.models.schemas import HotelOption, TravelProfile


class HotelProvider(Protocol):
    def search_hotels(self, profile: TravelProfile) -> List[HotelOption]:
        ...


@dataclass
class NullHotelProvider:
    def search_hotels(self, profile: TravelProfile) -> List[HotelOption]:
        return []

