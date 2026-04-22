from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol

from travel_planner.models.schemas import FoodOption, TravelProfile


class DiningProvider(Protocol):
    def search_dining(self, profile: TravelProfile) -> List[FoodOption]:
        ...


@dataclass
class NullDiningProvider:
    def search_dining(self, profile: TravelProfile) -> List[FoodOption]:
        return []

