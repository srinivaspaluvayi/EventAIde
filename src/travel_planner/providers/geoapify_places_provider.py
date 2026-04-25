from __future__ import annotations

from dataclasses import dataclass
from typing import List

import requests

from travel_planner.models.schemas import PlaceOption, TravelProfile
from travel_planner.utils.logging import get_logger

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"
_CATEGORY_GROUPS: tuple[str, ...] = (
    # Iconic landmarks
    "tourism.attraction,tourism.sights,heritage,heritage.unesco,man_made.tower,man_made.bridge,man_made.lighthouse",
    # Culture
    "entertainment.museum,entertainment.culture.gallery,entertainment.culture.theatre,tourism.sights.monastery,tourism.sights.place_of_worship",
    # Nature
    "natural,natural.water,natural.mountain,national_park,leisure.park,beach",
    # Family-friendly
    "entertainment.theme_park,entertainment.zoo,entertainment.aquarium,leisure.park",
)


@dataclass
class GeoapifyPlacesProvider:
    api_key: str
    radius_m: int = 8000
    max_results: int = 20
    timeout_seconds: int = 25

    def __post_init__(self) -> None:
        self._log = get_logger("travel_planner.geoapify_places")

    def search_places(self, profile: TravelProfile) -> List[PlaceOption]:
        if not self.api_key:
            self._log.warning("GEOAPIFY_API_KEY missing; skipping Geoapify places search")
            return []
        coords = self._geocode_destination(profile.destination)
        if coords is None:
            self._log.warning("Geoapify geocoding returned no coordinates for %r", profile.destination)
            return []
        lon, lat = coords
        all_features: list = []
        for cats in _CATEGORY_GROUPS:
            features = self._fetch_features(lon, lat, cats)
            if features is None:
                continue
            all_features.extend(features)
        if not all_features:
            # Hard fallback in case all groups fail or return empty.
            features = self._fetch_features(
                lon,
                lat,
                "tourism.attraction,tourism.sights,heritage,heritage.unesco,entertainment.museum,leisure.park,natural,national_park,man_made.tower,man_made.bridge",
            )
            if features is None:
                return []
            all_features = features
        if not all_features:
            return []

        out: List[PlaceOption] = []
        seen: set[str] = set()
        for feat in all_features:
            if not isinstance(feat, dict):
                continue
            props = feat.get("properties") if isinstance(feat.get("properties"), dict) else {}
            geom = feat.get("geometry") if isinstance(feat.get("geometry"), dict) else {}
            coords_list = geom.get("coordinates") if isinstance(geom.get("coordinates"), list) else []
            place = self._to_place_option(props, coords_list)
            if place is None:
                continue
            key = place.name.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(place)
            if len(out) >= self.max_results:
                break
        if out:
            out.sort(key=lambda x: x.rank_score, reverse=True)
            top_n = min(5, len(out))
            for i in range(top_n):
                out[i].must_see = True
        return out

    def _fetch_features(self, lon: float, lat: float, categories: str) -> list | None:
        base_limit = min(500, max(self.max_results * 3, 80))
        params: dict[str, str | int] = {
            "categories": categories,
            "filter": f"circle:{lon},{lat},{self.radius_m}",
            # Avoid over-prioritizing only nearest POIs in large cities.
            "limit": base_limit,
            "lang": "en",
            "apiKey": self.api_key,
        }
        try:
            response = requests.get(PLACES_URL, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.HTTPError as exc:
            self._log.warning("Geoapify places HTTP error: %s", exc)
            return None
        except requests.RequestException as exc:
            self._log.warning("Geoapify places request error: %s. Retrying with smaller query.", exc)
            retry_params = dict(params)
            retry_params["limit"] = max(30, self.max_results)
            retry_timeout = max(10, int(self.timeout_seconds * 0.8))
            try:
                retry_resp = requests.get(PLACES_URL, params=retry_params, timeout=retry_timeout)
                retry_resp.raise_for_status()
                payload = retry_resp.json()
                features = payload.get("features")
                return features if isinstance(features, list) else []
            except requests.RequestException as retry_exc:
                self._log.warning("Geoapify places retry failed: %s", retry_exc)
                return None
        payload = response.json()
        features = payload.get("features")
        return features if isinstance(features, list) else []

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

    def _to_place_option(self, props: dict, coords_list: list) -> PlaceOption | None:
        name = str(props.get("name") or props.get("address_line1") or "").strip()
        if not name:
            return None
        cats = props.get("categories")
        category = self._pick_category(cats)
        address = str(
            props.get("formatted")
            or props.get("address_line2")
            or props.get("address_line1")
            or props.get("city")
            or ""
        ).strip()
        distance = props.get("distance")
        try:
            distance_m = float(distance) if distance is not None else 0.0
        except (TypeError, ValueError):
            distance_m = 0.0
        lat = 0.0
        lon = 0.0
        if len(coords_list) >= 2:
            try:
                lon = float(coords_list[0])
                lat = float(coords_list[1])
            except (TypeError, ValueError):
                pass
        ds = props.get("datasource") if isinstance(props.get("datasource"), dict) else {}
        website = str(props.get("website") or ds.get("url") or "").strip()
        rank = self._rank_score(name=name, categories=cats, distance_m=distance_m)
        return PlaceOption(
            name=name,
            category=category,
            address=address,
            distance_m=max(0.0, distance_m),
            latitude=lat,
            longitude=lon,
            url=website,
            notes="[source:provider:geoapify] Attractions POI from Geoapify/OSM dataset.",
            rank_score=rank,
        )

    @staticmethod
    def _pick_category(categories: object) -> str:
        if not isinstance(categories, list):
            return "Attraction"
        for cat in categories:
            if not isinstance(cat, str):
                continue
            if cat.startswith("tourism.") or cat.startswith("entertainment.") or cat.startswith("heritage.") or cat.startswith("leisure."):
                return cat.replace(".", " / ").replace("_", " ").title()
        for cat in categories:
            if isinstance(cat, str):
                return cat.replace(".", " / ").replace("_", " ").title()
        return "Attraction"

    @staticmethod
    def _rank_score(name: str, categories: object, distance_m: float) -> float:
        score = 0.0
        lower_name = (name or "").lower()
        if isinstance(categories, list):
            for cat in categories:
                if not isinstance(cat, str):
                    continue
                if cat == "heritage.unesco":
                    score += 20
                elif cat.startswith("heritage"):
                    score += 12
                elif cat.startswith("tourism.attraction"):
                    score += 14
                elif cat.startswith("tourism.sights"):
                    score += 12
                elif cat.startswith("tourism.viewpoint"):
                    score += 8
                elif cat.startswith("entertainment.museum"):
                    score += 7
                elif cat.startswith("entertainment.gallery"):
                    score += 5
                elif cat.startswith("entertainment.culture.theatre"):
                    score += 5
                elif cat.startswith("leisure.park"):
                    score += 4
                elif cat.startswith("entertainment.zoo"):
                    score += 4
                elif cat.startswith("man_made.tower") or cat.startswith("man_made.bridge"):
                    score += 8
                elif cat.startswith("national_park"):
                    score += 7
                elif cat.startswith("natural"):
                    score += 5
                elif cat.startswith("beach"):
                    score += 5
        # Name heuristics for iconic landmarks.
        for token in (
            "museum",
            "cathedral",
            "tower",
            "palace",
            "monument",
            "bridge",
            "park",
            "square",
            "riverwalk",
            "pier",
            "gate",
            "institute",
            "aquarium",
        ):
            if token in lower_name:
                score += 1.5
        if distance_m > 0:
            score += max(0.0, 7.0 - (distance_m / 4500.0))
        return round(score, 3)

