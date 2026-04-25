from __future__ import annotations

from typing import Dict, List

from travel_planner.models.schemas import FinalPlan, FlightOption, Itinerary


def itinerary_cost_table(itinerary: Itinerary) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for day in itinerary.days:
        rows.append({"day": day.day, "cost_usd": round(day.day_total_usd, 2)})
    return rows


def estimated_flight_cost_usd(flights: list[FlightOption]) -> float:
    """Use the lowest returned option as default flight estimate."""
    if not flights:
        return 0.0
    return round(min(max(f.estimated_cost_usd, 0.0) for f in flights), 2)


def estimated_total_spend_usd(plan: FinalPlan, selected_flight_cost: float | None = None) -> float:
    itinerary_total = round(plan.itinerary.estimated_total_usd, 2)
    flight_total = (
        round(max(selected_flight_cost, 0.0), 2)
        if selected_flight_cost is not None
        else estimated_flight_cost_usd(plan.flights or [])
    )
    return round(itinerary_total + flight_total, 2)


def budget_summary_rows(
    plan: FinalPlan,
    selected_flight_cost: float | None = None,
    flight_label: str | None = None,
) -> List[Dict[str, float | str]]:
    itinerary_total = round(plan.itinerary.estimated_total_usd, 2)
    flight_total = (
        round(max(selected_flight_cost, 0.0), 2)
        if selected_flight_cost is not None
        else estimated_flight_cost_usd(plan.flights or [])
    )
    flight_row_label = (
        f"Flights ({flight_label})" if flight_label else "Flights (lowest option)"
    )
    return [
        {"item": "Itinerary activities", "cost_usd": itinerary_total},
        {"item": flight_row_label, "cost_usd": flight_total},
        {"item": "Estimated total", "cost_usd": round(itinerary_total + flight_total, 2)},
    ]


def flight_budget_options(flights: list[FlightOption]) -> list[tuple[str, float]]:
    return [
        (
            f"Flight {idx}: {f.route} ({f.airline}, ~${f.estimated_cost_usd:,.0f})",
            round(max(f.estimated_cost_usd, 0.0), 2),
        )
        for idx, f in enumerate(flights, start=1)
    ]


def selected_flight_context(plan: FinalPlan, selected_idx: int | None) -> tuple[str | None, float | None]:
    options = flight_budget_options(plan.flights or [])
    if not options:
        return None, None
    safe_idx = selected_idx if selected_idx is not None and 0 <= selected_idx < len(options) else 0
    label, cost = options[safe_idx]
    return label.split(":")[0], cost

