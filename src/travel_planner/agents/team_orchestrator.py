from __future__ import annotations

from dataclasses import dataclass

from travel_planner.agents.budget_optimizer_agent import BudgetOptimizerAgent
from travel_planner.agents.destination_research import DestinationResearchAgent
from travel_planner.agents.dining_agent import DiningAgent
from travel_planner.agents.flight_search_agent import FlightSearchAgent
from travel_planner.agents.hotel_search_agent import HotelSearchAgent
from travel_planner.agents.show_discovery_agent import ShowDiscoveryAgent
from travel_planner.models.schemas import BudgetPlan, DestinationInfo, FoodOption, FlightOption, HotelOption, ShowOption, TravelProfile


@dataclass
class TeamOutput:
    destination_info: DestinationInfo
    flights: list[FlightOption]
    hotels: list[HotelOption]
    dining: list[FoodOption]
    shows: list[ShowOption]
    budget_plan: BudgetPlan


class TravelPlanningTeam:
    def __init__(
        self,
        destination_agent: DestinationResearchAgent,
        flight_agent: FlightSearchAgent,
        hotel_agent: HotelSearchAgent,
        dining_agent: DiningAgent,
        show_agent: ShowDiscoveryAgent,
        budget_agent: BudgetOptimizerAgent,
    ) -> None:
        self.destination_agent = destination_agent
        self.flight_agent = flight_agent
        self.hotel_agent = hotel_agent
        self.dining_agent = dining_agent
        self.show_agent = show_agent
        self.budget_agent = budget_agent

    def run(self, profile: TravelProfile) -> TeamOutput:
        destination_info = self.destination_agent.run(profile=profile)
        flights = self.flight_agent.run(profile=profile)
        hotels = self.hotel_agent.run(profile=profile)
        dining = self.dining_agent.run(profile=profile)
        shows = self.show_agent.run(profile=profile)
        budget_plan = self.budget_agent.run(
            profile=profile,
            flights=flights,
            hotels=hotels,
            dining=dining,
        )
        return TeamOutput(
            destination_info=destination_info,
            flights=flights,
            hotels=hotels,
            dining=dining,
            shows=shows,
            budget_plan=budget_plan,
        )

