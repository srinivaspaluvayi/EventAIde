from __future__ import annotations

from travel_planner.agents.destination_research import DestinationResearchAgent
from travel_planner.agents.dining_agent import DiningAgent
from travel_planner.agents.flight_search_agent import FlightSearchAgent
from travel_planner.providers.flight_provider import NullFlightProvider
from travel_planner.providers.serpapi_flight_provider import SerpApiFlightProvider
from travel_planner.agents.hotel_search_agent import HotelSearchAgent
from travel_planner.agents.itinerary_planner import ItineraryPlannerAgent
from travel_planner.agents.logistics_agent import LogisticsAgent
from travel_planner.agents.places_discovery_agent import PlacesDiscoveryAgent
from travel_planner.agents.preference_collector import PreferenceCollectorAgent
from travel_planner.agents.show_discovery_agent import ShowDiscoveryAgent
from travel_planner.agents.summary_generator import SummaryGeneratorAgent
from travel_planner.agents.team_orchestrator import TravelPlanningTeam
from travel_planner.agents.budget_optimizer_agent import BudgetOptimizerAgent
from travel_planner.config.settings import Settings
from travel_planner.models.schemas import (
    FinalPlan,
    FlightOption,
    FlightTimeline,
    FoodOption,
    HotelOption,
    PlaceOption,
    ScenarioSummary,
    ShowOption,
)
from travel_planner.orchestration.agno_runtime import runtime_note
from travel_planner.providers.dining_provider import NullDiningProvider
from travel_planner.providers.geoapify_dining_provider import GeoapifyDiningProvider
from travel_planner.providers.geoapify_hotel_provider import GeoapifyHotelProvider
from travel_planner.providers.geoapify_places_provider import GeoapifyPlacesProvider
from travel_planner.providers.hotel_provider import NullHotelProvider
from travel_planner.providers.places_provider import NullPlacesProvider
from travel_planner.providers.show_provider import NullShowProvider
from travel_planner.providers.ticketmaster_show_provider import TicketmasterShowProvider
from travel_planner.utils.llm import SmallModelClient
from travel_planner.utils.logging import get_logger


class TravelPlannerPipeline:
    def __init__(self, settings: Settings) -> None:
        self.logger = get_logger("travel_planner.pipeline")
        self.runtime_metadata = runtime_note()
        self.logger.info("Pipeline initialized | %s", self.runtime_metadata)
        llm = SmallModelClient(api_key=settings.openai_api_key, model=settings.openai_model)
        self.preference_agent = PreferenceCollectorAgent(llm)
        self.research_agent = DestinationResearchAgent(llm, max_search_results=settings.max_search_results)
        if settings.serpapi_key:
            flight_provider = SerpApiFlightProvider(
                api_key=settings.serpapi_key,
                departure_id=settings.flight_departure_id,
                arrival_id_override=settings.flight_arrival_id,
            )
        else:
            flight_provider = NullFlightProvider()
        self.flight_agent = FlightSearchAgent(
            llm, provider=flight_provider, max_results=settings.flight_max_results
        )
        if settings.geoapify_api_key:
            hotel_provider = GeoapifyHotelProvider(
                api_key=settings.geoapify_api_key,
                radius_m=settings.geoapify_hotel_radius_m,
            )
        else:
            self.logger.warning(
                "GEOAPIFY_API_KEY is empty; hotels will use LLM fallback until a key is set"
            )
            hotel_provider = NullHotelProvider()
        self.hotel_agent = HotelSearchAgent(llm, provider=hotel_provider)
        if settings.geoapify_api_key:
            dining_provider = GeoapifyDiningProvider(
                api_key=settings.geoapify_api_key,
                radius_m=settings.geoapify_dining_radius_m,
                max_results=settings.dining_max_results,
            )
        else:
            self.logger.warning(
                "GEOAPIFY_API_KEY is empty; dining will use LLM fallback until a key is set"
            )
            dining_provider = NullDiningProvider()
        self.dining_agent = DiningAgent(
            llm, provider=dining_provider, max_results=settings.dining_max_results
        )
        if settings.geoapify_api_key:
            places_provider = GeoapifyPlacesProvider(
                api_key=settings.geoapify_api_key,
                radius_m=settings.geoapify_places_radius_m,
                max_results=settings.places_max_results,
            )
        else:
            self.logger.warning(
                "GEOAPIFY_API_KEY is empty; places-to-visit list will be unavailable"
            )
            places_provider = NullPlacesProvider()
        self.places_agent = PlacesDiscoveryAgent(provider=places_provider)
        if settings.ticketmaster_api_key:
            show_provider = TicketmasterShowProvider(
                api_key=settings.ticketmaster_api_key,
                max_results=settings.show_max_results,
            )
        else:
            self.logger.warning(
                "TICKETMASTER_API_KEY is empty; shows/events list will be unavailable"
            )
            show_provider = NullShowProvider()
        self.show_agent = ShowDiscoveryAgent(provider=show_provider)
        self.budget_agent = BudgetOptimizerAgent(llm)
        self.team = TravelPlanningTeam(
            destination_agent=self.research_agent,
            flight_agent=self.flight_agent,
            hotel_agent=self.hotel_agent,
            dining_agent=self.dining_agent,
            places_agent=self.places_agent,
            show_agent=self.show_agent,
            budget_agent=self.budget_agent,
        )
        self.itinerary_agent = ItineraryPlannerAgent(llm)
        self.logistics_agent = LogisticsAgent(llm)
        self.summary_agent = SummaryGeneratorAgent()

    def run(self, user_input: str) -> FinalPlan:
        self.logger.info("Starting pipeline run")
        profile = self.preference_agent.run(user_input=user_input)
        self.logger.info(
            "Profile parsed for destination=%s dates=%s..%s",
            profile.destination,
            profile.start_date,
            profile.end_date,
        )
        team_output = self.team.run(profile=profile)
        itinerary = self.itinerary_agent.run(
            profile=profile,
            destination_info=team_output.destination_info,
            flights=team_output.flights,
            hotels=team_output.hotels,
            dining=team_output.dining,
            shows=team_output.shows,
            places=team_output.places,
            budget_plan=team_output.budget_plan,
        )
        timeline = self.itinerary_agent.build_timeline(
            profile=profile,
            flights=team_output.flights,
            dining=team_output.dining,
            shows=team_output.shows,
            places=team_output.places,
        )
        flight_timelines: list[FlightTimeline] = []
        for idx, flight in enumerate(team_output.flights[:3], start=1):
            per_flight_entries = self.itinerary_agent.build_timeline(
                profile=profile,
                flights=[flight],
                dining=team_output.dining,
                shows=team_output.shows,
                places=team_output.places,
            )
            flight_timelines.append(
                FlightTimeline(
                    flight_label=f"Flight {idx}",
                    route=flight.route,
                    airline=flight.airline,
                    estimated_cost_usd=flight.estimated_cost_usd,
                    entries=per_flight_entries,
                )
            )
        logistics = self.logistics_agent.run(
            profile=profile,
            destination_info=team_output.destination_info,
            itinerary=itinerary,
            hotels=team_output.hotels,
            flights=team_output.flights,
        )
        html_path = self.summary_agent.run(
            profile=profile,
            destination_info=team_output.destination_info,
            itinerary=itinerary,
            logistics=logistics,
            flights=team_output.flights,
        )
        scenario_summary = self._build_scenario_summary(
            flights=team_output.flights,
            hotels=team_output.hotels,
            dining=team_output.dining,
            places=team_output.places,
            shows=team_output.shows,
        )
        return FinalPlan(
            profile=profile,
            destination_info=team_output.destination_info,
            itinerary=itinerary,
            logistics=logistics,
            flights=team_output.flights,
            hotels=team_output.hotels,
            dining=team_output.dining,
            places=team_output.places,
            shows=team_output.shows,
            timeline=timeline,
            flight_timelines=flight_timelines,
            scenario_summary=scenario_summary,
            budget_plan=team_output.budget_plan,
            html_path=html_path,
        )

    @staticmethod
    def _build_scenario_summary(
        flights: list[FlightOption],
        hotels: list[HotelOption],
        dining: list[FoodOption],
        places: list[PlaceOption],
        shows: list[ShowOption],
    ) -> ScenarioSummary:
        return ScenarioSummary(
            scenario_count=len(flights),
            provider_flights=sum(1 for f in flights if "[source:provider:serpapi]" in (f.notes or "")),
            fallback_flights=sum(1 for f in flights if "[source:fallback:llm]" in (f.notes or "")),
            provider_hotels=sum(
                1 for h in hotels if any("[source:provider:geoapify]" in (x or "") for x in (h.highlights or []))
            ),
            fallback_hotels=sum(
                1 for h in hotels if not any("[source:provider:geoapify]" in (x or "") for x in (h.highlights or []))
            ),
            provider_dining=sum(1 for d in dining if "[source:provider:geoapify]" in (d.notes or "")),
            fallback_dining=sum(1 for d in dining if "[source:fallback:llm]" in (d.notes or "")),
            provider_places=sum(1 for p in places if "[source:provider:geoapify]" in (p.notes or "")),
            fallback_places=sum(1 for p in places if "[source:provider:geoapify]" not in (p.notes or "")),
            provider_shows=sum(1 for s in shows if "[source:provider:ticketmaster]" in (s.notes or "")),
            fallback_shows=sum(1 for s in shows if "[source:provider:ticketmaster]" not in (s.notes or "")),
        )

