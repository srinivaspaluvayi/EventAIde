from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import List

import requests

from travel_planner.models.schemas import ShowOption, TravelProfile
from travel_planner.utils.logging import get_logger

DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"


@dataclass
class TicketmasterShowProvider:
    api_key: str
    max_results: int = 12
    timeout_seconds: int = 15

    def __post_init__(self) -> None:
        self._log = get_logger("travel_planner.ticketmaster")

    def search_shows(self, profile: TravelProfile) -> List[ShowOption]:
        if not self.api_key:
            return []
        city = (profile.destination or "").split(",")[0].strip()
        if not city:
            return []
        start_dt = datetime.combine(profile.start_date, time.min, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_dt = datetime.combine(profile.end_date, time.max, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        params: dict[str, str | int] = {
            "apikey": self.api_key,
            "city": city,
            "countryCode": "US",
            "startDateTime": start_dt,
            "endDateTime": end_dt,
            "size": max(1, min(int(self.max_results), 30)),
            "sort": "date,asc",
        }
        response = requests.get(DISCOVERY_URL, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        embedded = payload.get("_embedded") if isinstance(payload, dict) else None
        events = embedded.get("events") if isinstance(embedded, dict) else None
        if not isinstance(events, list):
            return []

        rows: List[ShowOption] = []
        seen: set[str] = set()
        for ev in events:
            if not isinstance(ev, dict):
                continue
            name = str(ev.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            venue = self._extract_venue(ev)
            when = self._extract_when(ev)
            price = self._extract_price(ev)
            url = str(ev.get("url") or "").strip()
            rows.append(
                ShowOption(
                    name=name,
                    venue=venue or city,
                    local_datetime=when or "TBA",
                    price_range_usd=price,
                    url=url,
                    notes="[source:provider:ticketmaster] Live event listing from Ticketmaster Discovery API.",
                )
            )
            if len(rows) >= self.max_results:
                break
        return rows

    @staticmethod
    def _extract_venue(ev: dict) -> str:
        emb = ev.get("_embedded")
        if not isinstance(emb, dict):
            return ""
        venues = emb.get("venues")
        if not isinstance(venues, list) or not venues:
            return ""
        first = venues[0]
        if not isinstance(first, dict):
            return ""
        return str(first.get("name") or "").strip()

    @staticmethod
    def _extract_when(ev: dict) -> str:
        dates = ev.get("dates")
        if not isinstance(dates, dict):
            return ""
        start = dates.get("start")
        if not isinstance(start, dict):
            return ""
        local_date = str(start.get("localDate") or "").strip()
        local_time = str(start.get("localTime") or "").strip()
        if local_date and local_time:
            return f"{local_date} {local_time}"
        return local_date

    @staticmethod
    def _extract_price(ev: dict) -> str:
        ranges = ev.get("priceRanges")
        if not isinstance(ranges, list) or not ranges:
            return "See Ticketmaster"
        first = ranges[0]
        if not isinstance(first, dict):
            return "See Ticketmaster"
        lo = first.get("min")
        hi = first.get("max")
        currency = str(first.get("currency") or "USD").upper()
        symbol = "$" if currency == "USD" else f"{currency} "
        try:
            if lo is not None and hi is not None:
                return f"{symbol}{float(lo):.0f}-{symbol}{float(hi):.0f}"
            if lo is not None:
                return f"From {symbol}{float(lo):.0f}"
        except Exception:
            return "See Ticketmaster"
        return "See Ticketmaster"

