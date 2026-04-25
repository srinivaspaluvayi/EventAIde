#!/usr/bin/env python3
"""Run each travel planner agent in pipeline order and print return health.

Usage (from repo root):
  PYTHONPATH=src .venv/bin/python scripts/run_agents_check.py
  PYTHONPATH=src .venv/bin/python scripts/run_agents_check.py "Your travel prompt here"

  PYTHONPATH=src .venv/bin/python scripts/run_agents_check.py --only dining

``--only`` still runs PreferenceCollector first (needs a structured ``TravelProfile``).

Does not print API keys or raw model completions.
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from travel_planner.agents.budget_optimizer_agent import BudgetOptimizerAgent
from travel_planner.agents.destination_research import DestinationResearchAgent
from travel_planner.agents.dining_agent import DiningAgent
from travel_planner.agents.flight_search_agent import FlightSearchAgent
from travel_planner.agents.hotel_search_agent import HotelSearchAgent
from travel_planner.agents.itinerary_planner import ItineraryPlannerAgent
from travel_planner.agents.logistics_agent import LogisticsAgent
from travel_planner.agents.places_discovery_agent import PlacesDiscoveryAgent
from travel_planner.agents.preference_collector import PreferenceCollectorAgent
from travel_planner.agents.summary_generator import SummaryGeneratorAgent
from travel_planner.config.settings import Settings
from travel_planner.providers.dining_provider import NullDiningProvider
from travel_planner.providers.flight_provider import NullFlightProvider
from travel_planner.providers.geoapify_dining_provider import GeoapifyDiningProvider
from travel_planner.providers.geoapify_hotel_provider import GeoapifyHotelProvider
from travel_planner.providers.geoapify_places_provider import GeoapifyPlacesProvider
from travel_planner.providers.hotel_provider import NullHotelProvider
from travel_planner.providers.places_provider import NullPlacesProvider
from travel_planner.providers.serpapi_flight_provider import SerpApiFlightProvider
from travel_planner.utils.llm import SmallModelClient


DEFAULT_PROMPT = (
    "Plan a 3-day trip to Chicago, IL for 2 adults June 10–12 2026, budget $1800 USD, "
    "interests: food and architecture, relaxed travel style."
)


def _line(status: str, agent: str, detail: str) -> None:
    print(f"{status:10} | {agent:22} | {detail}")


def _flight_detail(flights: list) -> str:
    if not flights:
        return "0 items"
    tags: list[str] = []
    for x in flights[:3]:
        n = x.notes or ""
        if "[source:provider:serpapi]" in n:
            tags.append("serpapi")
        elif "[source:fallback:llm]" in n:
            tags.append("llm")
        else:
            tags.append("?")
    return f"n={len(flights)} sample_tags={tags} first_route={flights[0].route!r}"


def _dining_detail(items: list) -> str:
    if not items:
        return "0 items"
    tags: list[str] = []
    for x in items[:3]:
        if "[source:provider:geoapify]" in (x.notes or ""):
            tags.append("geoapify")
        elif "[source:fallback:llm]" in (x.notes or ""):
            tags.append("llm")
        else:
            tags.append("?")
    return f"n={len(items)} sample_tags={tags} first={items[0].name!r}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run each agent and summarize outputs.")
    parser.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT, help="User prompt for PreferenceCollector")
    parser.add_argument(
        "--only",
        choices=[
            "preference",
            "destination",
            "flight",
            "hotel",
            "dining",
            "places",
            "budget",
            "itinerary",
            "logistics",
            "summary",
        ],
        help="Stop after this agent (earlier agents still run as prerequisites).",
    )
    args = parser.parse_args()
    stop_after = args.only

    settings = Settings.from_env()
    llm = SmallModelClient(api_key=settings.openai_api_key, model=settings.openai_model)

    if settings.geoapify_api_key:
        dining_provider = GeoapifyDiningProvider(
            api_key=settings.geoapify_api_key,
            radius_m=settings.geoapify_dining_radius_m,
            max_results=settings.dining_max_results,
        )
        dining_backend = "GeoapifyDiningProvider"
        hotel_provider = GeoapifyHotelProvider(
            api_key=settings.geoapify_api_key,
            radius_m=settings.geoapify_hotel_radius_m,
        )
        hotel_backend = "GeoapifyHotelProvider"
        places_provider = GeoapifyPlacesProvider(
            api_key=settings.geoapify_api_key,
            radius_m=settings.geoapify_places_radius_m,
            max_results=settings.places_max_results,
        )
        places_backend = "GeoapifyPlacesProvider"
    else:
        dining_provider = NullDiningProvider()
        hotel_provider = NullHotelProvider()
        places_provider = NullPlacesProvider()
        dining_backend = "NullDiningProvider (set GEOAPIFY_API_KEY)"
        hotel_backend = "NullHotelProvider (set GEOAPIFY_API_KEY)"
        places_backend = "NullPlacesProvider (set GEOAPIFY_API_KEY)"

    if settings.serpapi_key and settings.flight_departure_id:
        flight_provider = SerpApiFlightProvider(
            api_key=settings.serpapi_key,
            departure_id=settings.flight_departure_id,
            arrival_id_override=settings.flight_arrival_id,
        )
        flight_backend = "SerpApiFlightProvider"
    else:
        flight_provider = NullFlightProvider()
        flight_backend = "NullFlightProvider (set SERPAPI + FLIGHT_DEPARTURE_ID)"

    print("--- Agent check (no secrets printed) ---")
    print(
        f"model={settings.openai_model!r} flight_backend={flight_backend} "
        f"flight_max={settings.flight_max_results} | dining_backend={dining_backend} "
        f"dining_max_results={settings.dining_max_results} | hotel_backend={hotel_backend} "
        f"| places_backend={places_backend} places_max={settings.places_max_results}"
    )
    print()

    try:
        profile = PreferenceCollectorAgent(llm).run(user_input=args.prompt)
        _line(
            "OK" if profile.destination else "FAIL",
            "PreferenceCollector",
            f"destination={profile.destination!r} budget={profile.budget_usd} group={profile.group_size}",
        )
        if stop_after == "preference":
            return 0

        dest = DestinationResearchAgent(llm, max_search_results=settings.max_search_results).run(profile=profile)
        ok = bool(dest.highlights or dest.local_tips or dest.weather_summary)
        _line(
            "OK" if ok else "EMPTY",
            "DestinationResearch",
            f"highlights={len(dest.highlights)} tips={len(dest.local_tips)} visa_len={len(dest.visa_requirements)}",
        )
        if stop_after == "destination":
            return 0

        flights = FlightSearchAgent(
            llm, provider=flight_provider, max_results=settings.flight_max_results
        ).run(profile=profile)
        _line("OK" if flights else "EMPTY", "FlightSearch", _flight_detail(flights))
        if stop_after == "flight":
            return 0

        hotels = HotelSearchAgent(llm, provider=hotel_provider).run(profile=profile)
        _line("OK" if hotels else "EMPTY", "HotelSearch", f"n={len(hotels)}")
        if stop_after == "hotel":
            return 0

        dining = DiningAgent(
            llm, provider=dining_provider, max_results=settings.dining_max_results
        ).run(profile=profile)
        st = "OK" if dining else "EMPTY"
        _line(st, "Dining", _dining_detail(dining))
        if stop_after == "dining":
            return 0 if dining else 1

        places = PlacesDiscoveryAgent(provider=places_provider).run(profile=profile)
        _line("OK" if places else "EMPTY", "Places", f"n={len(places)}")
        if stop_after == "places":
            return 0 if places else 1

        budget = BudgetOptimizerAgent(llm).run(profile=profile, flights=flights, hotels=hotels, dining=dining)
        _line(
            "OK" if budget.total_planned_usd > 0 else "EMPTY",
            "BudgetOptimizer",
            f"total_planned_usd={budget.total_planned_usd}",
        )
        if stop_after == "budget":
            return 0

        itinerary = ItineraryPlannerAgent(llm).run(
            profile=profile,
            destination_info=dest,
            flights=flights,
            hotels=hotels,
            dining=dining,
            budget_plan=budget,
        )
        _line(
            "OK" if itinerary.days else "EMPTY",
            "ItineraryPlanner",
            f"title={itinerary.trip_title[:48]!r} days={len(itinerary.days)} est_total={itinerary.estimated_total_usd}",
        )
        if stop_after == "itinerary":
            return 0

        logistics = LogisticsAgent(llm).run(
            profile=profile,
            destination_info=dest,
            itinerary=itinerary,
            hotels=hotels,
            flights=flights,
        )
        ok = bool(logistics.accommodation_options and logistics.local_transport and logistics.packing_tips)
        _line(
            "OK" if ok else "EMPTY",
            "Logistics",
            f"acc={len(logistics.accommodation_options)} transport={len(logistics.local_transport)} pack={len(logistics.packing_tips)}",
        )
        if stop_after == "logistics":
            return 0

        path = SummaryGeneratorAgent().run(
            profile=profile, destination_info=dest, itinerary=itinerary, logistics=logistics
        )
        _line("OK" if path else "EMPTY", "SummaryGenerator", f"path={path!r}")

    except Exception as exc:
        print()
        print("FAIL | exception:", type(exc).__name__, str(exc)[:200])
        traceback.print_exc()
        return 1

    print()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
