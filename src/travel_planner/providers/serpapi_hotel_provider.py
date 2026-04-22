from __future__ import annotations

from dataclasses import dataclass
from typing import List

import requests

from travel_planner.models.schemas import HotelOption, TravelProfile


@dataclass
class SerpApiHotelProvider:
    api_key: str
    timeout_seconds: int = 15

    def search_hotels(self, profile: TravelProfile) -> List[HotelOption]:
        if not self.api_key:
            return []
        params = {
            "engine": "google_hotels",
            "q": f"hotels in {profile.destination}",
            "check_in_date": str(profile.start_date),
            "check_out_date": str(profile.end_date),
            "adults": max(profile.group_size, 1),
            "currency": "USD",
            "api_key": self.api_key,
        }
        response = requests.get("https://serpapi.com/search.json", params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        properties = payload.get("properties", [])
        results: List[HotelOption] = []
        for item in properties[:5]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            area = str(item.get("type", "Popular area")).strip()
            total_rate = item.get("total_rate", {}) if isinstance(item.get("total_rate"), dict) else {}
            price = str(total_rate.get("lowest", "")).strip()
            if not price:
                extracted_prices = item.get("extracted_hotel_class")
                price = f"${extracted_prices}" if extracted_prices else "See latest pricing"
            highlights = []
            for key in ("overall_rating", "reviews", "location_rating"):
                value = item.get(key)
                if value not in (None, "", []):
                    highlights.append(f"{key.replace('_', ' ').title()}: {value}")
            if not highlights:
                highlights = ["Check latest amenities and cancellation terms."]
            results.append(
                HotelOption(
                    name=name,
                    area=area,
                    price_range_usd=price,
                    highlights=highlights[:4],
                )
            )
        return results

