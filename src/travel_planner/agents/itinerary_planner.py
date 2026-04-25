from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from travel_planner.models.schemas import (
    BudgetPlan,
    DestinationInfo,
    FoodOption,
    FlightOption,
    HotelOption,
    Itinerary,
    PlaceOption,
    ShowOption,
    TimelineEntry,
    TravelProfile,
)
from travel_planner.utils.llm import SmallModelClient
from travel_planner.utils.validators import trip_days


SYSTEM_PROMPT = """
You are Agent 3 (Itinerary Planner).
Goal: build a realistic day-by-day plan grounded in provided trip context.

Requirements:
- Use all relevant context fields (destination info, budget, interests, weather, flight/hotel/dining hints).
- Keep each day practical: balanced effort, realistic travel pace, no overpacking.
- Maintain variety across interests while respecting budget constraints.
- Use neutral placeholders if specific entities are not provided in context.

Hard constraints:
- Do not invent concrete external facts (flight numbers, exact venues) unless present in context.
- Keep costs plausible.
- Ensure `day_total_usd` matches slot totals.
- Ensure `estimated_total_usd` matches sum of all days (allow small rounding differences only).

Output rules:
- Return JSON only, no markdown.
- Follow this exact schema:
{
  "trip_title": "...",
  "days": [
    {
      "day": 1,
      "morning": {"slot":"morning","title":"...","details":"...","estimated_cost_usd": 0},
      "afternoon": {"slot":"afternoon","title":"...","details":"...","estimated_cost_usd": 0},
      "evening": {"slot":"evening","title":"...","details":"...","estimated_cost_usd": 0},
      "day_total_usd": 0
    }
  ],
  "estimated_total_usd": 0
}
"""


class ItineraryPlannerAgent:
    def __init__(self, llm: SmallModelClient) -> None:
        self.llm = llm

    def run(
        self,
        profile: TravelProfile,
        destination_info: DestinationInfo,
        flights: list[FlightOption] | None = None,
        hotels: list[HotelOption] | None = None,
        dining: list[FoodOption] | None = None,
        shows: list[ShowOption] | None = None,
        places: list[PlaceOption] | None = None,
        budget_plan: BudgetPlan | None = None,
    ) -> Itinerary:
        days = min(trip_days(profile.start_date, profile.end_date), 10)
        if flights:
            flight_hint = " | ".join(
                f"{f.route} ({f.airline}, ~${f.estimated_cost_usd:.0f})" for f in flights[:3]
            )
        else:
            flight_hint = "Best-route option"
        hotel_hint = hotels[0].name if hotels else "Central stay option"
        dining_hint = dining[0].name if dining else "Local food hall"
        budget_hint = budget_plan.total_planned_usd if budget_plan else profile.budget_usd
        show_hint = ", ".join(f"{s.name} @ {s.local_datetime}" for s in (shows or [])[:3]) or "No timed events"
        place_hint = ", ".join(p.name for p in (places or [])[:5]) or "No places"
        prompt = (
            f"Destination: {profile.destination}\n"
            f"Days: {days}\n"
            f"Budget USD: {profile.budget_usd}\n"
            f"Style: {profile.travel_style}\n"
            f"Interests: {', '.join(profile.interests)}\n"
            f"Highlights: {', '.join(destination_info.highlights)}\n"
            f"Weather: {destination_info.weather_summary}\n"
            f"Flight context: {flight_hint}\n"
            f"Hotel context: {hotel_hint}\n"
            f"Dining context: {dining_hint}\n"
            f"Events context: {show_hint}\n"
            f"Places context: {place_hint}\n"
            f"Budget target total: {budget_hint}\n"
        )
        try:
            parsed = self.llm.run_json(SYSTEM_PROMPT, prompt, max_tokens=1200)
            itinerary = Itinerary(**parsed)
            return self._sanitize_itinerary(itinerary)
        except Exception:
            days_payload = []
            daily_budget = profile.budget_usd / max(days, 1)
            for day in range(1, days + 1):
                morning_cost = round(daily_budget * 0.25, 2)
                afternoon_cost = round(daily_budget * 0.45, 2)
                evening_cost = round(daily_budget * 0.30, 2)
                total = round(morning_cost + afternoon_cost + evening_cost, 2)
                days_payload.append(
                    {
                        "day": day,
                        "morning": {
                            "slot": "morning",
                            "title": "Local breakfast and walking tour",
                            "details": "Start in a central neighborhood and visit nearby highlights.",
                            "estimated_cost_usd": morning_cost,
                        },
                        "afternoon": {
                            "slot": "afternoon",
                            "title": "Main activity block",
                            "details": f"Focus on {profile.interests[0] if profile.interests else 'popular attractions'}.",
                            "estimated_cost_usd": afternoon_cost,
                        },
                        "evening": {
                            "slot": "evening",
                            "title": "Dinner and relaxed exploration",
                            "details": "End with local cuisine and a low-intensity activity.",
                            "estimated_cost_usd": evening_cost,
                        },
                        "day_total_usd": total,
                    }
                )
            total_est = round(sum(day["day_total_usd"] for day in days_payload), 2)
            return Itinerary(trip_title=f"{profile.destination} Trip Plan", days=days_payload, estimated_total_usd=total_est)

    def _sanitize_itinerary(self, itinerary: Itinerary) -> Itinerary:
        # Remove common hallucinated specificity when not grounded.
        blocked_tokens = [
            "los angeles",
            "new york city",
            "katz",
            "check-in at",
            "flight number",
        ]

        def _clean_text(value: str) -> str:
            text = value.strip()
            lower = text.lower()
            if any(token in lower for token in blocked_tokens):
                return "Planned activity based on your preferences and local availability."
            return text

        for day in itinerary.days:
            day.morning.title = _clean_text(day.morning.title)
            day.morning.details = _clean_text(day.morning.details)
            day.afternoon.title = _clean_text(day.afternoon.title)
            day.afternoon.details = _clean_text(day.afternoon.details)
            day.evening.title = _clean_text(day.evening.title)
            day.evening.details = _clean_text(day.evening.details)
        return itinerary

    @dataclass
    class _TripAnchor:
        title: str
        start: datetime
        end: datetime
        source: str

    @dataclass
    class _ScheduledItem:
        date: date
        window: str
        title: str
        source: str
        start: datetime | None = None
        end: datetime | None = None
        notes: str = ""

    def build_timeline(
        self,
        profile: TravelProfile,
        flights: list[FlightOption] | None,
        dining: list[FoodOption] | None,
        shows: list[ShowOption] | None,
        places: list[PlaceOption] | None,
    ) -> list[TimelineEntry]:
        days = trip_days(profile.start_date, profile.end_date)
        if days <= 0:
            return []
        items: list[ItineraryPlannerAgent._ScheduledItem] = []
        # 1) flight anchors
        anchors = self._build_flight_anchors(profile, flights or [])
        for a in anchors:
            items.append(
                self._ScheduledItem(
                    date=a.start.date(),
                    window="anchor",
                    title=a.title,
                    source=a.source,
                    start=a.start,
                    end=a.end,
                )
            )
        # 2) daily meal slots
        self._add_meal_slots(profile, dining or [], items)
        # 3) timed events with conflict handling
        self._add_events(profile, shows or [], items)
        # 4) fill free windows with places
        self._add_places(profile, places or [], items)
        # 5) sort and convert
        items.sort(key=lambda x: ((x.start or datetime.combine(x.date, time.min)), x.window))
        return [
            TimelineEntry(
                day=(it.date - profile.start_date).days + 1,
                date=str(it.date),
                window=it.window,
                title=it.title,
                source=it.source,
                start_local=it.start.strftime("%Y-%m-%d %H:%M") if it.start else "",
                end_local=it.end.strftime("%Y-%m-%d %H:%M") if it.end else "",
                notes=it.notes,
            )
            for it in items
        ]

    def _build_flight_anchors(self, profile: TravelProfile, flights: list[FlightOption]) -> list[_TripAnchor]:
        if not flights:
            return []
        chosen = flights[:3]
        out: list[ItineraryPlannerAgent._TripAnchor] = []
        travel_buffer_after = timedelta(hours=2)
        travel_buffer_before = timedelta(hours=3)
        for idx, f in enumerate(chosen, start=1):
            arr = self._extract_anchor_time(f.outbound_raw, arrival=True)
            dep = self._extract_anchor_time(f.return_raw, arrival=False)
            if arr:
                out.append(
                    self._TripAnchor(
                        title=f"Flight {idx} arrival: {f.route}",
                        start=arr,
                        end=arr + travel_buffer_after,
                        source="flight",
                    )
                )
            if dep:
                out.append(
                    self._TripAnchor(
                        title=f"Flight {idx} return departure: {f.route}",
                        start=dep - travel_buffer_before,
                        end=dep,
                        source="flight",
                    )
                )
        return out

    def _extract_anchor_time(self, bundle: dict, arrival: bool) -> datetime | None:
        if not isinstance(bundle, dict):
            return None
        legs = bundle.get("flights")
        if not isinstance(legs, list) or not legs:
            return None
        leg = legs[-1] if arrival else legs[0]
        if not isinstance(leg, dict):
            return None
        key = "arrival_airport" if arrival else "departure_airport"
        ap = leg.get(key)
        if not isinstance(ap, dict):
            return None
        t = ap.get("time")
        if not isinstance(t, str):
            return None
        try:
            return datetime.strptime(t.strip(), "%Y-%m-%d %H:%M")
        except Exception:
            return None

    def _add_meal_slots(
        self,
        profile: TravelProfile,
        dining: list[FoodOption],
        items: list[_ScheduledItem],
    ) -> None:
        meal_defs = (
            ("breakfast", time(8, 0), time(9, 0)),
            ("lunch", time(13, 0), time(14, 0)),
            ("dinner", time(19, 0), time(20, 30)),
        )
        pool = dining or [FoodOption(name="Local dining option", cuisine="Local", price_level="$$", notes="fallback")]
        di = 0
        first_arrival_dt, return_block_start = self._presence_bounds(items)
        for d in self._date_range(profile.start_date, profile.end_date):
            for meal_name, st, en in meal_defs:
                start_dt = datetime.combine(d, st)
                end_dt = datetime.combine(d, en)
                if not self._is_within_presence_window(
                    start_dt=start_dt,
                    end_dt=end_dt,
                    first_arrival_dt=first_arrival_dt,
                    return_block_start=return_block_start,
                ):
                    continue
                if self._conflicts(items, start_dt, end_dt):
                    continue
                place = pool[di % len(pool)]
                di += 1
                items.append(
                    self._ScheduledItem(
                        date=d,
                        window=meal_name,
                        title=f"{meal_name.title()}: {place.name}",
                        source="dining",
                        start=start_dt,
                        end=end_dt,
                        notes=f"{place.cuisine} · {place.price_level}",
                    )
                )

    def _add_events(self, profile: TravelProfile, shows: list[ShowOption], items: list[_ScheduledItem]) -> None:
        first_arrival_dt, return_block_start = self._presence_bounds(items)
        for s in shows:
            dt = self._parse_local_datetime(s.local_datetime)
            if dt is None:
                continue
            if dt.date() < profile.start_date or dt.date() > profile.end_date:
                continue
            end_dt = dt + timedelta(hours=2)
            if not self._is_within_presence_window(
                start_dt=dt,
                end_dt=end_dt,
                first_arrival_dt=first_arrival_dt,
                return_block_start=return_block_start,
            ):
                continue
            if self._conflicts(items, dt, end_dt):
                continue
            items.append(
                self._ScheduledItem(
                    date=dt.date(),
                    window=self._window_for_hour(dt.hour),
                    title=f"Event: {s.name}",
                    source="event",
                    start=dt,
                    end=end_dt,
                    notes=f"{s.venue} · {s.price_range_usd}",
                )
            )

    def _add_places(self, profile: TravelProfile, places: list[PlaceOption], items: list[_ScheduledItem]) -> None:
        ordered = sorted(places, key=lambda p: (not p.must_see, -p.rank_score, p.distance_m))
        if not ordered:
            return
        pi = 0
        first_arrival_dt, return_block_start = self._presence_bounds(items)
        for d in self._date_range(profile.start_date, profile.end_date):
            for window, st, en in (
                ("morning", time(10, 0), time(11, 30)),
                ("afternoon", time(15, 0), time(17, 0)),
            ):
                start_dt = datetime.combine(d, st)
                end_dt = datetime.combine(d, en)
                if not self._is_within_presence_window(
                    start_dt=start_dt,
                    end_dt=end_dt,
                    first_arrival_dt=first_arrival_dt,
                    return_block_start=return_block_start,
                ):
                    continue
                if self._window_taken(items, d, window) or self._conflicts(items, start_dt, end_dt):
                    continue
                place = ordered[pi % len(ordered)]
                pi += 1
                label = "Must See" if place.must_see else "Place"
                items.append(
                    self._ScheduledItem(
                        date=d,
                        window=window,
                        title=f"{label}: {place.name}",
                        source="place",
                        start=start_dt,
                        end=end_dt,
                        notes=f"{place.category} · {place.distance_m:.0f}m",
                    )
                )

    @staticmethod
    def _parse_local_datetime(value: str) -> datetime | None:
        raw = (value or "").strip()
        if not raw:
            return None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw, fmt)
                if fmt == "%Y-%m-%d":
                    return datetime.combine(dt.date(), time(19, 0))
                return dt
            except Exception:
                continue
        return None

    @staticmethod
    def _window_for_hour(hour: int) -> str:
        if hour < 12:
            return "morning"
        if hour < 17:
            return "afternoon"
        return "evening"

    @staticmethod
    def _conflicts(items: list[_ScheduledItem], start: datetime, end: datetime) -> bool:
        for it in items:
            if not it.start or not it.end:
                continue
            if start < it.end and end > it.start:
                return True
        return False

    @staticmethod
    def _window_taken(items: list[_ScheduledItem], d: date, window: str) -> bool:
        for it in items:
            if it.date == d and it.window == window:
                return True
        return False

    @staticmethod
    def _date_range(start_d: date, end_d: date) -> list[date]:
        days = (end_d - start_d).days
        if days < 0:
            return []
        return [start_d + timedelta(days=i) for i in range(days + 1)]

    @staticmethod
    def _presence_bounds(items: list[_ScheduledItem]) -> tuple[datetime | None, datetime | None]:
        first_arrival_dt: datetime | None = None
        return_block_start: datetime | None = None
        for it in items:
            if it.source != "flight":
                continue
            title = (it.title or "").lower()
            if "arrival" in title and it.start is not None:
                if first_arrival_dt is None or it.start < first_arrival_dt:
                    first_arrival_dt = it.start
            if "return departure" in title and it.start is not None:
                if return_block_start is None or it.start > return_block_start:
                    return_block_start = it.start
        return first_arrival_dt, return_block_start

    @staticmethod
    def _is_within_presence_window(
        start_dt: datetime,
        end_dt: datetime,
        first_arrival_dt: datetime | None,
        return_block_start: datetime | None,
    ) -> bool:
        if first_arrival_dt is not None and end_dt <= first_arrival_dt:
            return False
        if return_block_start is not None and start_dt >= return_block_start:
            return False
        return True

