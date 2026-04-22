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


class FinalPlan(BaseModel):
    profile: TravelProfile
    destination_info: DestinationInfo
    itinerary: Itinerary
    logistics: Logistics
    html_path: str

