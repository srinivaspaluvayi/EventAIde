from datetime import date

from travel_planner.models.schemas import TravelProfile
from travel_planner.providers.geoapify_places_provider import GEOCODE_URL, PLACES_URL, GeoapifyPlacesProvider


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _profile() -> TravelProfile:
    return TravelProfile(
        destination="Chicago",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 3),
        budget_usd=1800,
        travel_style="balanced",
        interests=["culture"],
        group_size=1,
        departure_id="STL",
        arrival_id="ORD",
    )


def test_geoapify_places_provider_maps_and_dedupes(monkeypatch) -> None:
    geocode_payload = {"results": [{"lon": -87.6298, "lat": 41.8781}]}
    places_payload = {
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": [-87.62, 41.88]},
                "properties": {
                    "name": "Cloud Gate",
                    "formatted": "201 E Randolph St, Chicago, IL",
                    "distance": 750,
                    "categories": ["tourism.sights"],
                    "website": "https://example.org/cloud-gate",
                },
            },
            {
                "geometry": {"type": "Point", "coordinates": [-87.62, 41.88]},
                "properties": {
                    "name": "Cloud Gate",
                    "formatted": "Duplicate",
                    "distance": 760,
                    "categories": ["tourism.sights"],
                },
            },
        ]
    }

    def _fake_get(url, params=None, timeout=0):  # noqa: ARG001
        if url == GEOCODE_URL:
            return _FakeResponse(geocode_payload)
        if url == PLACES_URL:
            return _FakeResponse(places_payload)
        raise AssertionError("unexpected URL")

    monkeypatch.setattr("travel_planner.providers.geoapify_places_provider.requests.get", _fake_get)

    provider = GeoapifyPlacesProvider(api_key="test", max_results=20)
    rows = provider.search_places(_profile())

    assert len(rows) == 1
    row = rows[0]
    assert row.name == "Cloud Gate"
    assert row.category == "Tourism / Sights"
    assert row.address.startswith("201 E Randolph")
    assert row.distance_m == 750
    assert row.latitude == 41.88
    assert row.longitude == -87.62
    assert "geoapify" in row.notes.lower()
    assert row.rank_score > 0
    assert row.must_see is True


def test_geoapify_places_provider_returns_empty_when_no_api_key() -> None:
    provider = GeoapifyPlacesProvider(api_key="")
    rows = provider.search_places(_profile())
    assert rows == []

