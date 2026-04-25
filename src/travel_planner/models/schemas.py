from __future__ import annotations

from datetime import date
from typing import List

from pydantic import BaseModel, Field


class TravelProfile(BaseModel):
    destination: str = Field(..., min_length=2)
    start_date: date
    end_date: date
    budget_usd: float = Field(..., gt=0)
    travel_style: str
    interests: List[str]
    group_size: int = Field(..., ge=1, le=20)
    departure_id: str = ""
    arrival_id: str = ""
    clarifying_questions: List[str] = Field(default_factory=list)


class DestinationInfo(BaseModel):
    highlights: List[str]
    best_areas_to_stay: List[str]
    local_tips: List[str]
    visa_requirements: str
    weather_summary: str
    sources: List[str] = Field(default_factory=list)


class Activity(BaseModel):
    slot: str
    title: str
    details: str
    estimated_cost_usd: float = Field(..., ge=0)


class DayPlan(BaseModel):
    day: int
    morning: Activity
    afternoon: Activity
    evening: Activity
    day_total_usd: float = Field(..., ge=0)


class Itinerary(BaseModel):
    trip_title: str
    days: List[DayPlan]
    estimated_total_usd: float = Field(..., ge=0)


class Logistics(BaseModel):
    accommodation_options: List[str]
    local_transport: List[str]
    packing_tips: List[str]


class FlightOption(BaseModel):
    route: str
    airline: str
    estimated_cost_usd: float = Field(..., ge=0)
    notes: str


class HotelOption(BaseModel):
    name: str
    area: str
    price_range_usd: str
    highlights: List[str] = Field(default_factory=list)


class FoodOption(BaseModel):
    name: str
    cuisine: str
    price_level: str
    notes: str


class ShowOption(BaseModel):
    name: str
    venue: str
    local_datetime: str
    price_range_usd: str
    url: str = ""
    notes: str = ""


class BudgetPlan(BaseModel):
    transportation_usd: float = Field(..., ge=0)
    stay_usd: float = Field(..., ge=0)
    food_usd: float = Field(..., ge=0)
    activities_usd: float = Field(..., ge=0)
    buffer_usd: float = Field(..., ge=0)
    total_planned_usd: float = Field(..., ge=0)
    optimization_tips: List[str] = Field(default_factory=list)


class FinalPlan(BaseModel):
    profile: TravelProfile
    destination_info: DestinationInfo
    itinerary: Itinerary
    logistics: Logistics
    flights: List[FlightOption] = Field(default_factory=list)
    hotels: List[HotelOption] = Field(default_factory=list)
    dining: List[FoodOption] = Field(default_factory=list)
    shows: List[ShowOption] = Field(default_factory=list)
    budget_plan: BudgetPlan | None = None
    html_path: str

