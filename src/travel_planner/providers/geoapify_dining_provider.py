from __future__ import annotations

from dataclasses import dataclass
from typing import List

import requests

from travel_planner.models.schemas import FoodOption, TravelProfile
from travel_planner.utils.logging import get_logger

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"

# See https://apidocs.geoapify.com/docs/places/#categories
_DEFAULT_CATERING_CATEGORIES = (
    "catering.restaurant,catering.cafe,catering.fast_food,catering.food_court,catering.bar"
)


@dataclass
class GeoapifyDiningProvider:
    """Dining POIs via [Geoapify Places API](https://apidocs.geoapify.com/docs/places/) (OSM-backed).

    Flow: forward-geocode ``profile.destination`` → ``filter=circle:lon,lat,radius_m`` + categories.
    """

    api_key: str
    radius_m: int = 8000
    max_results: int = 30
    timeout_seconds: int = 15

    def __post_init__(self) -> None:
        self._log = get_logger("travel_planner.geoapify")

    def search_dining(self, profile: TravelProfile) -> List[FoodOption]:
        if not self.api_key:
            self._log.warning("GEOAPIFY_API_KEY missing; skipping Geoapify dining search")
            return []
        coords = self._geocode_destination(profile.destination)
        if coords is None:
            self._log.warning("Geoapify geocoding returned no coordinates for %r", profile.destination)
            return []
        lon, lat = coords
        categories, conditions = self._categories_and_conditions(profile)
        # Request extra POIs so dedupe / unnamed skips still yield up to max_results.
        places_limit = min(500, max(self.max_results * 2, 40))
        params: dict[str, str | int] = {
            "categories": categories,
            "filter": f"circle:{lon},{lat},{self.radius_m}",
            "bias": f"proximity:{lon},{lat}",
            "limit": places_limit,
            "lang": "en",
            "apiKey": self.api_key,
        }
        if conditions:
            params["conditions"] = conditions
        response = requests.get(PLACES_URL, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        features = payload.get("features") or []
        budget_label = self._budget_label(profile.budget_usd)
        results: List[FoodOption] = []
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
            cuisine = self._cuisine_from_categories(props.get("categories"))
            city = str(props.get("city") or "").strip()
            state = str(props.get("state") or "").strip()
            place_ctx = f"{city}, {state}".strip(", ").strip() or profile.destination
            results.append(
                FoodOption(
                    name=name,
                    cuisine=cuisine,
                    price_level=budget_label,
                    notes=(
                        f"[source:provider:geoapify] Near {place_ctx} (OSM/Geoapify POI data); "
                        f"best for {profile.travel_style} travel — verify hours and bookings."
                    ),
                )
            )
            if len(results) >= self.max_results:
                break
        return results

    def _geocode_destination(self, destination: str) -> tuple[float, float] | None:
        text = (destination or "").strip()
        if not text:
            return None
        params = {
            "text": text,
            "limit": 1,
            "format": "json",
            "apiKey": self.api_key,
        }
        response = requests.get(GEOCODE_URL, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        # ``format=json`` → ``results`` array; GeoJSON default → ``features`` + Point geometry
        results = data.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                lon, lat = first.get("lon"), first.get("lat")
                try:
                    return (float(lon), float(lat))
                except (TypeError, ValueError):
                    pass
        features = data.get("features")
        if isinstance(features, list) and features:
            geom = features[0].get("geometry") if isinstance(features[0], dict) else None
            if isinstance(geom, dict) and geom.get("type") == "Point":
                coords = geom.get("coordinates")
                if isinstance(coords, list) and len(coords) >= 2:
                    try:
                        return (float(coords[0]), float(coords[1]))
                    except (TypeError, ValueError):
                        pass
            props = features[0].get("properties") if isinstance(features[0], dict) else None
            if isinstance(props, dict):
                lon, lat = props.get("lon"), props.get("lat")
                try:
                    return (float(lon), float(lat))
                except (TypeError, ValueError):
                    pass
        return None

    def _categories_and_conditions(self, profile: TravelProfile) -> tuple[str, str]:
        lower = [i.lower().strip() for i in profile.interests if i.strip()]
        if any("vegan" in i for i in lower):
            return _DEFAULT_CATERING_CATEGORIES, "vegan"
        if any("vegetarian" in i or "veggie" in i for i in lower):
            return _DEFAULT_CATERING_CATEGORIES, "vegetarian"
        return _DEFAULT_CATERING_CATEGORIES, ""

    @staticmethod
    def _cuisine_from_categories(categories: object) -> str:
        if not isinstance(categories, list):
            return "Local cuisine"
        for cat in categories:
            if not isinstance(cat, str):
                continue
            if cat.startswith("catering.restaurant.") and len(cat) > len("catering.restaurant."):
                return cat.replace("catering.restaurant.", "").replace("_", " ").title()
            if cat.startswith("catering.cafe"):
                return "Cafe"
            if cat.startswith("catering.bar"):
                return "Bar"
        for cat in categories:
            if isinstance(cat, str) and cat.startswith("catering."):
                return cat.replace("catering.", "").replace("_", " ").title()
        return "Local cuisine"

    @staticmethod
    def _budget_label(budget_usd: float) -> str:
        if budget_usd < 900:
            return "$"
        if budget_usd < 2500:
            return "$$"
        return "$$$"
