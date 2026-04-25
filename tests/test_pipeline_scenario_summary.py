from __future__ import annotations

from travel_planner.models.schemas import FlightOption, FoodOption, HotelOption, PlaceOption, ShowOption
from travel_planner.orchestration.pipeline import TravelPlannerPipeline


def test_scenario_summary_counts_provider_vs_fallback() -> None:
    summary = TravelPlannerPipeline._build_scenario_summary(
        flights=[
            FlightOption(route="A", airline="X", estimated_cost_usd=100, notes="[source:provider:serpapi] ok"),
            FlightOption(route="B", airline="Y", estimated_cost_usd=200, notes="[source:fallback:llm] fallback"),
        ],
        hotels=[
            HotelOption(name="H1", area="Loop", price_range_usd="$$", highlights=["[source:provider:geoapify] good"]),
            HotelOption(name="H2", area="Loop", price_range_usd="$$", highlights=["fallback"]),
        ],
        dining=[
            FoodOption(name="D1", cuisine="American", price_level="$$", notes="[source:provider:geoapify]"),
            FoodOption(name="D2", cuisine="Pizza", price_level="$$", notes="[source:fallback:llm]"),
        ],
        places=[
            PlaceOption(name="P1", category="Sights", address="A", notes="[source:provider:geoapify]"),
            PlaceOption(name="P2", category="Park", address="B", notes="unknown"),
        ],
        shows=[
            ShowOption(name="S1", venue="V", local_datetime="2026-01-01 20:00", price_range_usd="$$", notes="[source:provider:ticketmaster]"),
            ShowOption(name="S2", venue="V", local_datetime="2026-01-01 20:00", price_range_usd="$$", notes="other"),
        ],
    )
    assert summary.scenario_count == 2
    assert summary.provider_flights == 1
    assert summary.fallback_flights == 1
    assert summary.provider_hotels == 1
    assert summary.fallback_hotels == 1
    assert summary.provider_dining == 1
    assert summary.fallback_dining == 1
    assert summary.provider_places == 1
    assert summary.fallback_places == 1
    assert summary.provider_shows == 1
    assert summary.fallback_shows == 1
