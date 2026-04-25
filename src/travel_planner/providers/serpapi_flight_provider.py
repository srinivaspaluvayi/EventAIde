from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List

import serpapi

from travel_planner.config.defaults import DEFAULT_ARRIVAL_ID, DEFAULT_DEPARTURE_ID
from travel_planner.models.schemas import FlightOption, TravelProfile
from travel_planner.providers.serpapi_util import serpapi_search_api_error
from travel_planner.utils.us_airports import normalize_us_iata
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
        self._log.info(
            "SerpAPI flight resolved inputs: dep=%s arr=%s dates=%s..%s pax=%s",
            dep,
            arrival,
            profile.start_date,
            profile.end_date,
            max(profile.group_size, 1),
        )
        params: dict[str, str | int] = {
            "engine": "google_flights",
            "departure_id": dep,
            "arrival_id": arrival,
            "outbound_date": str(profile.start_date),
            "return_date": str(profile.end_date),
            "currency": "USD",
            "hl": "en",
            "adults": max(profile.group_size, 1),
        }
        if profile.end_date > profile.start_date:
            params["type"] = "1"
        else:
            params["type"] = "2"
            params.pop("return_date", None)

        self._log.debug("SerpAPI google_flights search params (api_key via client only): %s", params)
        try:
            payload_raw = self._client.search(params, timeout=self.timeout_seconds)
        except serpapi.SerpApiError as exc:
            self._log.warning("SerpAPI flight search failed: %s", exc)
            return []
        payload_full = payload_raw.as_dict() if hasattr(payload_raw, "as_dict") else dict(payload_raw)
        self._log.info(
            "SerpAPI flight payload diagnostics: type=%s has_get=%s payload=%r",
            type(payload_raw).__name__,
            hasattr(payload_raw, "get"),
            payload_full,
        )

        api_err = serpapi_search_api_error(payload_full)
        if api_err:
            self._log.warning(
                "SerpAPI flight API error: %s | dep=%s arr=%s outbound=%s return=%s type=%s",
                api_err,
                params.get("departure_id"),
                params.get("arrival_id"),
                params.get("outbound_date"),
                params.get("return_date"),
                params.get("type"),
            )
            return []

        bundles: list[dict] = []
        best_n = 0
        other_n = 0
        for key in ("best_flights", "other_flights"):
            raw = payload_full.get(key)
            if isinstance(raw, list):
                if key == "best_flights":
                    best_n = len(raw)
                if key == "other_flights":
                    other_n = len(raw)
                bundles.extend([b for b in raw if isinstance(b, dict)])
        self._log.info(
            "SerpAPI flight payload summary: best=%s other=%s merged=%s",
            best_n,
            other_n,
            len(bundles),
        )
        results: List[FlightOption] = []
        is_roundtrip = profile.end_date > profile.start_date
        selected_bundles = self._select_roundtrip_price_tiers(bundles, target_count=3) if is_roundtrip else bundles
        if is_roundtrip:
            self._log.info(
                "SerpAPI round-trip tier selection: selected=%s from total=%s",
                len(selected_bundles),
                len(bundles),
            )
        dropped_no_price = 0
        dropped_no_legs = 0
        for bundle in selected_bundles:
            opt = self._bundle_to_option(bundle, profile, dep, arrival)
            if opt is None:
                if not isinstance(bundle.get("flights"), list) or not bundle.get("flights"):
                    dropped_no_legs += 1
                else:
                    dropped_no_price += 1
                continue
            if is_roundtrip:
                dep_token = bundle.get("departure_token")
                if isinstance(dep_token, str) and dep_token.strip():
                    return_bundle = self._search_best_return_bundle(params, dep_token.strip())
                    if return_bundle is not None:
                        return_opt = self._bundle_to_option(return_bundle, profile, arrival, dep)
                        if return_opt is not None:
                            # Keep outbound/first-call fare as the main estimate to avoid
                            # double-counting when Google Flights already reports round-trip totals.
                            opt.notes += (
                                f" Return option: {return_opt.route} ({return_opt.airline})"
                                f" ~${return_opt.estimated_cost_usd:.0f} USD."
                            )
                            opt.return_details = self._bundle_leg_summary(return_bundle)
                            opt.return_raw = dict(return_bundle)
            results.append(opt)
        self._log.info(
            "SerpAPI flight mapping summary: kept=%s dropped_no_legs=%s dropped_no_price=%s",
            len(results),
            dropped_no_legs,
            dropped_no_price,
        )
        return results

    def _search_best_return_bundle(self, params: dict[str, str | int], departure_token: str) -> dict[str, Any] | None:
        return_params = {**params, "departure_token": departure_token}
        try:
            payload_raw = self._client.search(return_params, timeout=self.timeout_seconds)
            payload = payload_raw.as_dict() if hasattr(payload_raw, "as_dict") else dict(payload_raw)
        except serpapi.SerpApiError as exc:
            self._log.warning("SerpAPI return flight search failed: %s", exc)
            return None
        api_err = serpapi_search_api_error(payload)
        if api_err:
            self._log.warning("SerpAPI return flight API error: %s", api_err)
            return None
        bundles: list[dict[str, Any]] = []
        for key in ("best_flights", "other_flights"):
            raw = payload.get(key)
            if isinstance(raw, list):
                bundles.extend([b for b in raw if isinstance(b, dict)])
        return bundles[0] if bundles else None

    def _select_roundtrip_price_tiers(self, bundles: list[dict], target_count: int) -> list[dict]:
        priced: list[tuple[float, int, dict]] = []
        for idx, bundle in enumerate(bundles):
            price = self._bundle_price(bundle)
            if price is None:
                continue
            priced.append((price, idx, bundle))
        if not priced:
            return []
        priced.sort(key=lambda x: x[0])
        if len(priced) <= target_count:
            return [b for _, _, b in priced]
        low = priced[0]
        mid = priced[len(priced) // 2]
        high = priced[-1]
        picks = [low, mid, high]
        seen_idx: set[int] = set()
        selected: list[dict] = []
        for _, idx, bundle in picks:
            if idx in seen_idx:
                continue
            seen_idx.add(idx)
            selected.append(bundle)
        if len(selected) < target_count:
            for _, idx, bundle in priced:
                if idx in seen_idx:
                    continue
                selected.append(bundle)
                seen_idx.add(idx)
                if len(selected) >= target_count:
                    break
        return selected[:target_count]

    @staticmethod
    def _bundle_price(bundle: dict) -> float | None:
        raw = bundle.get("price")
        try:
            value = float(raw)
            return value if value > 0 else None
        except (TypeError, ValueError):
            return None

    def _resolve_departure_id(self, profile: TravelProfile) -> str:
        p = normalize_us_iata(profile.departure_id)
        if p:
            return p
        e = normalize_us_iata(self.departure_id)
        if e:
            return e
        return DEFAULT_DEPARTURE_ID

    def _resolve_arrival_id(self, profile: TravelProfile) -> str:
        p = normalize_us_iata(profile.arrival_id)
        if p:
            return p
        o = normalize_us_iata(self.arrival_id_override)
        if o:
            return o
        m = re.search(r"\b([A-Z]{3})\b", profile.destination.upper())
        if m:
            d = normalize_us_iata(m.group(1))
            if d:
                return d
        return DEFAULT_ARRIVAL_ID

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
            outbound_details=self._bundle_leg_summary(bundle),
            outbound_raw=dict(bundle),
        )

    def _bundle_leg_summary(self, bundle: dict) -> str:
        legs = bundle.get("flights")
        if not isinstance(legs, list) or not legs:
            return ""
        parts: list[str] = []
        for idx, leg in enumerate(legs, start=1):
            if not isinstance(leg, dict):
                continue
            dep = leg.get("departure_airport") if isinstance(leg.get("departure_airport"), dict) else {}
            arr = leg.get("arrival_airport") if isinstance(leg.get("arrival_airport"), dict) else {}
            dep_code = str(dep.get("id") or "?")
            arr_code = str(arr.get("id") or "?")
            dep_time = str(dep.get("time") or "").strip()
            arr_time = str(arr.get("time") or "").strip()
            airline = str(leg.get("airline") or "").strip()
            flight_no = str(leg.get("flight_number") or "").strip()
            dur = leg.get("duration")
            dur_text = f" ~{int(dur)}m" if isinstance(dur, (int, float)) else ""
            seg_name = " ".join(x for x in [airline, flight_no] if x).strip() or f"Segment {idx}"
            parts.append(f"{seg_name}: {dep_code} {dep_time} -> {arr_code} {arr_time}{dur_text}".strip())
        stop_count = max(0, len(legs) - 1)
        total_dur = bundle.get("total_duration")
        total_text = f"total ~{int(total_dur)}m" if isinstance(total_dur, (int, float)) else "total duration N/A"
        stops_text = f"{stop_count} stop{'s' if stop_count != 1 else ''}"
        if not parts:
            return f"{stops_text}; {total_text}"
        return f"{stops_text}; {total_text} | " + " | ".join(parts)
