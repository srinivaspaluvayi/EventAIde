from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

import serpapi

from travel_planner.models.schemas import FlightOption, TravelProfile
from travel_planner.providers.serpapi_util import serpapi_search_api_error
from travel_planner.utils.logging import get_logger


@dataclass
class SerpApiFlightProvider:
    """Round-trip / one-way flight bundles.

    Uses the SerpAPI [Search API](https://serpapi.com/search-api) with ``engine=google_flights``;
    see [Google Flights API](https://serpapi.com/google-flights-api) for engine-specific parameters.
    """

    api_key: str
    departure_id: str
    arrival_id_override: str = ""
    timeout_seconds: int = 25
    max_results: int = 12

    def __post_init__(self) -> None:
        self._log = get_logger("travel_planner.serpapi_flights")
        self._client = serpapi.Client(api_key=self.api_key)

    def search_flights(self, profile: TravelProfile) -> List[FlightOption]:
        if not self.api_key:
            return []
        dep = self._resolve_departure_id(profile)
        if not dep:
            self._log.info("SerpAPI flights skipped: provide departure airport IATA in prompt or FLIGHT_DEPARTURE_ID.")
            return []
        arrival = self._resolve_arrival_id(profile)
        if not arrival:
            self._log.info(
                "SerpAPI flights skipped: set FLIGHT_ARRIVAL_ID or include a 3-letter IATA code in destination (e.g. ORD)."
            )
            return []
        params: dict[str, str | int] = {
            "engine": "google_flights",
            "departure_id": dep,
            "arrival_id": arrival,
            "outbound_date": str(profile.start_date),
            "currency": "USD",
            "hl": "en",
            "adults": max(profile.group_size, 1),
        }
        if profile.end_date > profile.start_date:
            params["type"] = "1"
            params["return_date"] = str(profile.end_date)
        else:
            params["type"] = "2"

        self._log.debug("SerpAPI google_flights search params (api_key via client only): %s", params)
        try:
            payload = self._client.search(params, timeout=self.timeout_seconds)
        except serpapi.SerpApiError as exc:
            self._log.warning("SerpAPI flight search failed: %s", exc)
            return []

        api_err = serpapi_search_api_error(payload)
        if api_err:
            self._log.warning("SerpAPI flight search returned API error: %s", api_err)
            return []

        bundles: list[dict] = []
        for key in ("best_flights", "other_flights"):
            raw = payload.get(key)
            if isinstance(raw, list):
                bundles.extend([b for b in raw if isinstance(b, dict)])
        results: List[FlightOption] = []
        seen: set[tuple[str, str, float]] = set()
        for bundle in bundles:
            opt = self._bundle_to_option(bundle, profile, dep, arrival)
            if opt is None:
                continue
            sig = (opt.route.lower(), opt.airline.lower(), round(opt.estimated_cost_usd, 2))
            if sig in seen:
                continue
            seen.add(sig)
            results.append(opt)
            if len(results) >= self.max_results:
                break
        return results

    def _resolve_departure_id(self, profile: TravelProfile) -> str:
        p = (profile.departure_id or "").strip().upper()
        if re.fullmatch(r"[A-Z]{3}", p):
            return p
        e = (self.departure_id or "").strip().upper()
        if re.fullmatch(r"[A-Z]{3}", e):
            return e
        return ""

    def _resolve_arrival_id(self, profile: TravelProfile) -> str:
        p = (profile.arrival_id or "").strip().upper()
        if re.fullmatch(r"[A-Z]{3}", p):
            return p
        o = (self.arrival_id_override or "").strip().upper()
        if re.fullmatch(r"[A-Z]{3}", o):
            return o
        m = re.search(r"\b([A-Z]{3})\b", profile.destination.upper())
        if m:
            return m.group(1)
        return ""

    def _bundle_to_option(
        self, bundle: dict, profile: TravelProfile, dep_id: str, arr_id: str
    ) -> FlightOption | None:
        legs = bundle.get("flights")
        if not isinstance(legs, list) or not legs:
            return None
        first = legs[0] if isinstance(legs[0], dict) else {}
        last = legs[-1] if isinstance(legs[-1], dict) else {}
        d0 = first.get("departure_airport") if isinstance(first.get("departure_airport"), dict) else {}
        a_last = last.get("arrival_airport") if isinstance(last.get("arrival_airport"), dict) else {}
        d_code = str(d0.get("id", dep_id))
        a_code = str(a_last.get("id", arr_id))
        stops = max(0, len(legs) - 1)
        route = f"{d_code} → {a_code}" if stops == 0 else f"{d_code} → … → {a_code} ({stops} stop{'s' if stops != 1 else ''})"
        airlines: list[str] = []
        for leg in legs:
            if isinstance(leg, dict) and leg.get("airline"):
                airlines.append(str(leg["airline"]))
        airline = airlines[0] if len(set(airlines)) <= 1 else "Multiple carriers"

        raw_price = bundle.get("price")
        try:
            price_total = float(raw_price)
        except (TypeError, ValueError):
            price_total = 0.0
        if price_total <= 0:
            return None

        total_dur = bundle.get("total_duration")
        dur_note = f" ~{int(total_dur)} min total" if isinstance(total_dur, (int, float)) else ""

        notes = (
            f"[source:provider:serpapi] Google Flights (SerpAPI) estimate for {profile.group_size} adult(s); "
            f"round-trip total shown ~${price_total:.0f} USD{dur_note}. "
            "Fares change — confirm on airline or OTA before booking."
        )
        return FlightOption(
            route=route,
            airline=airline,
            estimated_cost_usd=round(price_total, 2),
            notes=notes,
        )
