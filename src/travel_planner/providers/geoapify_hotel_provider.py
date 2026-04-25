from __future__ import annotations

from dataclasses import dataclass
from typing import List

import requests

from travel_planner.models.schemas import HotelOption, TravelProfile
from travel_planner.utils.logging import get_logger

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"


@dataclass
class GeoapifyHotelProvider:
    """Hotel POIs via Geoapify Places API (OSM-backed)."""

    api_key: str
    radius_m: int = 10000
    max_results: int = 5
    timeout_seconds: int = 15

    def __post_init__(self) -> None:
        self._log = get_logger("travel_planner.geoapify_hotels")

    def search_hotels(self, profile: TravelProfile) -> List[HotelOption]:
        if not self.api_key:
            return []
        coords = self._geocode_destination(profile.destination)
        if coords is None:
            self._log.warning("Geoapify hotel geocoding returned no coordinates for %r", profile.destination)
            return []
        lon, lat = coords
        params: dict[str, str | int] = {
            "categories": "accommodation.hotel,accommodation.motel,accommodation.hostel,accommodation.guest_house",
            "filter": f"circle:{lon},{lat},{self.radius_m}",
            "bias": f"proximity:{lon},{lat}",
            "limit": min(100, max(self.max_results * 3, 25)),
            "lang": "en",
            "apiKey": self.api_key,
        }
        response = requests.get(PLACES_URL, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        features = payload.get("features") or []
        results: List[HotelOption] = []
        seen: set[str] = set()
        for feat in features:
            if not isinstance(feat, dict):
                continue
            props = feat.get("properties") if isinstance(feat.get("properties"), dict) else {}
            name = str(props.get("name") or props.get("address_line1") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            area = self._area_text(props, profile.destination)
            price_band = self._price_range_from_budget(profile.budget_usd)
            highlights = [
                "[source:provider:geoapify] OSM/Geoapify accommodation listing",
                "Verify final nightly rates and cancellation policy on booking platform.",
            ]
            stars = props.get("stars")
            if isinstance(stars, (int, float)) and float(stars) > 0:
                highlights.insert(1, f"Rated around {float(stars):.1f} stars in source metadata.")
            results.append(
                HotelOption(
                    name=name,
                    area=area,
                    price_range_usd=price_band,
                    highlights=highlights[:4],
                )
            )
            if len(results) >= self.max_results:
                break
        return results

    def _geocode_destination(self, destination: str) -> tuple[float, float] | None:
        text = (destination or "").strip()
        if not text:
            return None
        params = {"text": text, "limit": 1, "format": "json", "apiKey": self.api_key}
        response = requests.get(GEOCODE_URL, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        results = data.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                lon, lat = first.get("lon"), first.get("lat")
                try:
                    return float(lon), float(lat)
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _area_text(props: dict, fallback_destination: str) -> str:
        city = str(props.get("city") or "").strip()
        state = str(props.get("state") or "").strip()
        district = str(props.get("district") or props.get("suburb") or "").strip()
        if district and city:
            return f"{district}, {city}"
        if city and state:
            return f"{city}, {state}"
        if city:
            return city
        return fallback_destination

    @staticmethod
    def _price_range_from_budget(budget_usd: float) -> str:
        if budget_usd < 1000:
            return "$60-$130/night"
        if budget_usd < 2500:
            return "$110-$220/night"
        return "$180-$350/night"

