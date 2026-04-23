from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol

from travel_planner.models.schemas import FlightOption, TravelProfile


class FlightProvider(Protocol):
    def search_flights(self, profile: TravelProfile) -> List[FlightOption]:
        ...


@dataclass
class NullFlightProvider:
    def search_flights(self, profile: TravelProfile) -> List[FlightOption]:
        return []
