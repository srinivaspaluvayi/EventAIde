from datetime import date

from travel_planner.models.schemas import TravelProfile
from travel_planner.providers.serpapi_flight_provider import SerpApiFlightProvider


class _FakeClient:
    def __init__(self, first_payload: dict, return_payload_by_token: dict[str, dict]) -> None:
        self.first_payload = first_payload
        self.return_payload_by_token = return_payload_by_token
        self.calls: list[dict] = []

    def search(self, params: dict, timeout: int = 0):  # noqa: ARG002
        self.calls.append(dict(params))
        token = params.get("departure_token")
        if isinstance(token, str):
            return self.return_payload_by_token.get(token, {"best_flights": []})
        return self.first_payload


def _profile_roundtrip() -> TravelProfile:
    return TravelProfile(
        destination="Chicago",
        start_date=date(2026, 5, 10),
        end_date=date(2026, 5, 15),
        budget_usd=2000,
        travel_style="balanced",
        interests=["food"],
        group_size=1,
        departure_id="STL",
        arrival_id="ORD",
    )


def _bundle(dep: str, arr: str, airline: str, price: float, token: str = "") -> dict:
    payload = {
        "flights": [
            {
                "departure_airport": {"id": dep},
                "arrival_airport": {"id": arr},
                "airline": airline,
            }
        ],
        "price": price,
    }
    if token:
        payload["departure_token"] = token
    return payload


def test_roundtrip_selects_three_tiers_and_fetches_return_details() -> None:
    first = {
        "best_flights": [
            _bundle("STL", "ORD", "A", 100, "t100"),
            _bundle("STL", "ORD", "B", 200, "t200"),
            _bundle("STL", "ORD", "C", 300, "t300"),
            _bundle("STL", "ORD", "D", 400, "t400"),
            _bundle("STL", "ORD", "E", 500, "t500"),
        ],
        "other_flights": [],
    }
    returns = {
        "t100": {"best_flights": [_bundle("ORD", "STL", "R1", 91)]},
        "t300": {"best_flights": [_bundle("ORD", "STL", "R2", 92)]},
        "t500": {"best_flights": [_bundle("ORD", "STL", "R3", 93)]},
    }
    provider = SerpApiFlightProvider(api_key="x", departure_id="STL", arrival_id_override="ORD")
    fake = _FakeClient(first_payload=first, return_payload_by_token=returns)
    provider._client = fake

    rows = provider.search_flights(_profile_roundtrip())

    assert len(rows) == 3
    assert sorted([r.estimated_cost_usd for r in rows]) == [100.0, 300.0, 500.0]
    assert all("Return option:" in r.notes for r in rows)
    tokens = [c.get("departure_token") for c in fake.calls if "departure_token" in c]
    assert tokens == ["t100", "t300", "t500"]


def test_one_way_does_not_call_return_lookup() -> None:
    first = {
        "best_flights": [
            _bundle("STL", "ORD", "A", 120, "t120"),
            _bundle("STL", "ORD", "B", 220, "t220"),
        ],
        "other_flights": [],
    }
    provider = SerpApiFlightProvider(api_key="x", departure_id="STL", arrival_id_override="ORD")
    fake = _FakeClient(first_payload=first, return_payload_by_token={})
    provider._client = fake
    p = _profile_roundtrip()
    p.end_date = p.start_date

    rows = provider.search_flights(p)

    assert len(rows) == 2
    assert all("Return option:" not in r.notes for r in rows)
    assert all("departure_token" not in c for c in fake.calls)


def test_roundtrip_without_token_keeps_outbound_row() -> None:
    first = {"best_flights": [_bundle("STL", "ORD", "A", 180)], "other_flights": []}
    provider = SerpApiFlightProvider(api_key="x", departure_id="STL", arrival_id_override="ORD")
    fake = _FakeClient(first_payload=first, return_payload_by_token={})
    provider._client = fake

    rows = provider.search_flights(_profile_roundtrip())

    assert len(rows) == 1
    assert "Return option:" not in rows[0].notes

