from __future__ import annotations

from travel_planner.agents.destination_research import DestinationResearchAgent
from travel_planner.agents.dining_agent import DiningAgent
from travel_planner.agents.flight_search_agent import FlightSearchAgent
from travel_planner.agents.hotel_search_agent import HotelSearchAgent
from travel_planner.agents.itinerary_planner import ItineraryPlannerAgent
from travel_planner.agents.logistics_agent import LogisticsAgent
from travel_planner.agents.preference_collector import PreferenceCollectorAgent
from travel_planner.agents.summary_generator import SummaryGeneratorAgent
from travel_planner.agents.team_orchestrator import TravelPlanningTeam
from travel_planner.agents.budget_optimizer_agent import BudgetOptimizerAgent
from travel_planner.config.settings import Settings
from travel_planner.models.schemas import FinalPlan
from travel_planner.orchestration.agno_runtime import runtime_note
from travel_planner.providers.foursquare_dining_provider import FoursquareDiningProvider
from travel_planner.providers.serpapi_hotel_provider import SerpApiHotelProvider
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
        self.flight_agent = FlightSearchAgent(llm)
        self.hotel_agent = HotelSearchAgent(llm, provider=SerpApiHotelProvider(api_key=settings.serpapi_key))
        self.dining_agent = DiningAgent(llm, provider=FoursquareDiningProvider(api_key=settings.foursquare_api_key))
        self.budget_agent = BudgetOptimizerAgent(llm)
        self.team = TravelPlanningTeam(
            destination_agent=self.research_agent,
            flight_agent=self.flight_agent,
            hotel_agent=self.hotel_agent,
            dining_agent=self.dining_agent,
            budget_agent=self.budget_agent,
        )
        self.itinerary_agent = ItineraryPlannerAgent(llm)
        self.logistics_agent = LogisticsAgent(llm)
        self.summary_agent = SummaryGeneratorAgent()

    def run(self, user_input: str) -> FinalPlan:
        self.logger.info("Starting pipeline run")
        profile = self.preference_agent.run(user_input=user_input)
        self.logger.info("Profile parsed for destination=%s", profile.destination)
        team_output = self.team.run(profile=profile)
        itinerary = self.itinerary_agent.run(
            profile=profile,
            destination_info=team_output.destination_info,
            flights=team_output.flights,
            hotels=team_output.hotels,
            dining=team_output.dining,
            budget_plan=team_output.budget_plan,
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
        )
        return FinalPlan(
            profile=profile,
            destination_info=team_output.destination_info,
            itinerary=itinerary,
            logistics=logistics,
            flights=team_output.flights,
            hotels=team_output.hotels,
            dining=team_output.dining,
            budget_plan=team_output.budget_plan,
            html_path=html_path,
        )

