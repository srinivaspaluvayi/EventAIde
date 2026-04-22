from __future__ import annotations

from dataclasses import dataclass
from typing import List

import requests

from travel_planner.models.schemas import FoodOption, TravelProfile


@dataclass
class FoursquareDiningProvider:
    api_key: str
    timeout_seconds: int = 12

    def search_dining(self, profile: TravelProfile) -> List[FoodOption]:
        if not self.api_key:
            return []
        headers = {
            "Authorization": self.api_key,
            "Accept": "application/json",
        }
        params = {
            "query": "restaurants",
            "near": profile.destination,
            "limit": 8,
            "sort": "RELEVANCE",
        }
        response = requests.get(
            "https://api.foursquare.com/v3/places/search",
            headers=headers,
            params=params,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        places = payload.get("results", [])
        results: List[FoodOption] = []
        for item in places[:5]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            categories = item.get("categories", [])
            cuisine = "Local cuisine"
            if isinstance(categories, list) and categories:
                first = categories[0] if isinstance(categories[0], dict) else {}
                cuisine = str(first.get("name", cuisine)).strip() or cuisine
            location = item.get("location", {}) if isinstance(item.get("location"), dict) else {}
            area = str(location.get("locality", profile.destination)).strip()
            results.append(
                FoodOption(
                    name=name,
                    cuisine=cuisine,
                    price_level="$$",
                    notes=f"Popular in {area}. Check latest hours before visiting.",
                )
            )
        return results

