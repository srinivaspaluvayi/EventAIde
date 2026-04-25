from __future__ import annotations

from datetime import date

from travel_planner.agents.itinerary_planner import ItineraryPlannerAgent
from travel_planner.models.schemas import FlightOption, FoodOption, PlaceOption, ShowOption, TravelProfile


class _StubLLM:
    def run_json(self, *_args, **_kwargs):
        raise RuntimeError("not used")


def _profile() -> TravelProfile:
    return TravelProfile(
        destination="Chicago",
        start_date=date(2026, 4, 23),
        end_date=date(2026, 4, 24),
        budget_usd=1200,
        travel_style="balanced",
        interests=["food", "culture"],
        group_size=1,
        departure_id="STL",
        arrival_id="ORD",
    )


def test_timeline_adds_flight_anchors_with_buffers() -> None:
    agent = ItineraryPlannerAgent(llm=_StubLLM())
    profile = _profile()
    flights = [
        FlightOption(
            route="STL -> ORD",
            airline="Airline A",
            estimated_cost_usd=200,
            notes="",
            outbound_raw={"flights": [{"arrival_airport": {"time": "2026-04-23 09:00"}}]},
            return_raw={"flights": [{"departure_airport": {"time": "2026-04-24 20:00"}}]},
        )
    ]

    timeline = agent.build_timeline(profile=profile, flights=flights, dining=[], shows=[], places=[])

    assert any(t.source == "flight" and t.window == "anchor" and t.start_local.endswith("09:00") for t in timeline)
    assert any(t.source == "flight" and t.window == "anchor" and t.end_local.endswith("20:00") for t in timeline)


def test_timeline_creates_three_meal_slots_per_day() -> None:
    agent = ItineraryPlannerAgent(llm=_StubLLM())
    profile = _profile()
    dining = [FoodOption(name="Cafe 1", cuisine="American", price_level="$$", notes="")]

    timeline = agent.build_timeline(profile=profile, flights=[], dining=dining, shows=[], places=[])
    meal_rows = [t for t in timeline if t.source == "dining"]

    assert len(meal_rows) == 6
    assert sorted({m.window for m in meal_rows}) == ["breakfast", "dinner", "lunch"]


def test_timeline_skips_conflicting_event_with_anchor() -> None:
    agent = ItineraryPlannerAgent(llm=_StubLLM())
    profile = _profile()
    flights = [
        FlightOption(
            route="STL -> ORD",
            airline="Airline A",
            estimated_cost_usd=200,
            notes="",
            outbound_raw={"flights": [{"arrival_airport": {"time": "2026-04-23 18:00"}}]},
            return_raw={},
        )
    ]
    shows = [ShowOption(name="Late Show", venue="Venue", local_datetime="2026-04-23 18:30", price_range_usd="$$")]

    timeline = agent.build_timeline(profile=profile, flights=flights, dining=[], shows=shows, places=[])

    assert any(t.source == "flight" for t in timeline)
    assert not any(t.source == "event" and "Late Show" in t.title for t in timeline)


def test_timeline_places_prioritize_must_see() -> None:
    agent = ItineraryPlannerAgent(llm=_StubLLM())
    profile = _profile()
    places = [
        PlaceOption(name="Regular Spot", category="Park", address="A", rank_score=20, must_see=False, distance_m=300),
        PlaceOption(name="Iconic Spot", category="Museum", address="B", rank_score=50, must_see=True, distance_m=500),
    ]

    timeline = agent.build_timeline(profile=profile, flights=[], dining=[], shows=[], places=places)
    place_rows = [t for t in timeline if t.source == "place"]

    assert place_rows
    assert place_rows[0].title.startswith("Must See: Iconic Spot")


def test_timeline_skips_meals_before_late_arrival_same_day() -> None:
    agent = ItineraryPlannerAgent(llm=_StubLLM())
    profile = _profile()
    flights = [
        FlightOption(
            route="STL -> ORD",
            airline="Airline A",
            estimated_cost_usd=200,
            notes="",
            outbound_raw={"flights": [{"arrival_airport": {"time": "2026-04-23 22:19"}}]},
            return_raw={},
        )
    ]
    dining = [FoodOption(name="Cafe 1", cuisine="American", price_level="$$", notes="")]

    timeline = agent.build_timeline(profile=profile, flights=flights, dining=dining, shows=[], places=[])
    day1_meals = [
        t
        for t in timeline
        if t.source == "dining" and t.date == "2026-04-23" and t.window in {"breakfast", "lunch", "dinner"}
    ]

    assert day1_meals == []
