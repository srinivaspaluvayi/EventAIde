from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol

from travel_planner.models.schemas import ShowOption, TravelProfile


class ShowProvider(Protocol):
    def search_shows(self, profile: TravelProfile) -> List[ShowOption]:
        ...


@dataclass
class NullShowProvider:
    def search_shows(self, profile: TravelProfile) -> List[ShowOption]:
        return []

