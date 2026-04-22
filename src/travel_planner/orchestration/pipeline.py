from __future__ import annotations

from travel_planner.agents.destination_research import DestinationResearchAgent
from travel_planner.agents.itinerary_planner import ItineraryPlannerAgent
from travel_planner.agents.logistics_agent import LogisticsAgent
from travel_planner.agents.preference_collector import PreferenceCollectorAgent
from travel_planner.agents.summary_generator import SummaryGeneratorAgent
from travel_planner.config.settings import Settings
from travel_planner.models.schemas import FinalPlan
from travel_planner.orchestration.agno_runtime import runtime_note
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
        self.itinerary_agent = ItineraryPlannerAgent(llm)
        self.logistics_agent = LogisticsAgent(llm)
        self.summary_agent = SummaryGeneratorAgent()

    def run(self, user_input: str) -> FinalPlan:
        self.logger.info("Starting pipeline run")
        profile = self.preference_agent.run(user_input=user_input)
        self.logger.info("Profile parsed for destination=%s", profile.destination)
        destination_info = self.research_agent.run(profile=profile)
        itinerary = self.itinerary_agent.run(profile=profile, destination_info=destination_info)
        logistics = self.logistics_agent.run(profile=profile, destination_info=destination_info, itinerary=itinerary)
        html_path = self.summary_agent.run(
            profile=profile,
            destination_info=destination_info,
            itinerary=itinerary,
            logistics=logistics,
        )
        return FinalPlan(
            profile=profile,
            destination_info=destination_info,
            itinerary=itinerary,
            logistics=logistics,
            html_path=html_path,
        )

