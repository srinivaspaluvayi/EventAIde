from __future__ import annotations

from datetime import date

from travel_planner.models.schemas import (
    DestinationInfo,
    FinalPlan,
    FlightOption,
    Itinerary,
    Logistics,
    TravelProfile,
)
from travel_planner.utils.costing import (
    budget_summary_rows,
    estimated_total_spend_usd,
    flight_budget_options,
    selected_flight_context,
)


def _plan() -> FinalPlan:
    return FinalPlan(
        profile=TravelProfile(
            destination="Chicago",
            start_date=date(2026, 4, 25),
            end_date=date(2026, 4, 28),
            budget_usd=2200,
            travel_style="balanced",
            interests=["food", "culture"],
            group_size=1,
        ),
        destination_info=DestinationInfo(
            highlights=["Millennium Park"],
            best_areas_to_stay=["Loop"],
            local_tips=["Use transit card"],
            visa_requirements="None",
            weather_summary="Mild",
        ),
        itinerary=Itinerary(trip_title="Test", days=[], estimated_total_usd=1000),
        logistics=Logistics(accommodation_options=[], local_transport=[], packing_tips=[]),
        flights=[
            FlightOption(route="STL -> ORD", airline="A", estimated_cost_usd=300, notes=""),
            FlightOption(route="STL -> ORD", airline="B", estimated_cost_usd=500, notes=""),
        ],
        html_path="output/travel_plan.html",
    )


def test_flight_budget_options_and_selected_context() -> None:
    plan = _plan()
    options = flight_budget_options(plan.flights)
    assert len(options) == 2
    assert "Flight 1:" in options[0][0]
    label, cost = selected_flight_context(plan, selected_idx=1)
    assert label == "Flight 2"
    assert cost == 500


def test_budget_rows_and_total_use_selected_flight() -> None:
    plan = _plan()
    rows = budget_summary_rows(plan, selected_flight_cost=500, flight_label="Flight 2")
    assert rows[1]["item"] == "Flights (Flight 2)"
    assert rows[1]["cost_usd"] == 500
    assert estimated_total_spend_usd(plan, selected_flight_cost=500) == 1500
