from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from travel_planner.config.defaults import (
    DEFAULT_DINING_MAX_RESULTS,
    DEFAULT_FLIGHT_MAX_RESULTS,
    DEFAULT_GEOAPIFY_DINING_RADIUS_M,
    DEFAULT_MAX_SEARCH_RESULTS,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_SHOW_MAX_RESULTS,
    MAX_DINING_MAX_RESULTS,
    MAX_FLIGHT_MAX_RESULTS,
    MAX_GEOAPIFY_DINING_RADIUS_M,
    MAX_MAX_SEARCH_RESULTS,
    MAX_SHOW_MAX_RESULTS,
    MIN_DINING_MAX_RESULTS,
    MIN_FLIGHT_MAX_RESULTS,
    MIN_GEOAPIFY_DINING_RADIUS_M,
    MIN_MAX_SEARCH_RESULTS,
    MIN_SHOW_MAX_RESULTS,
    DEFAULT_DEPARTURE_ID,
    DEFAULT_ARRIVAL_ID,
)
from travel_planner.utils.us_airports import normalize_us_iata

# Anchor .env to the project root (parent of `src/`) so API keys load even when the
# process cwd is not the repository (e.g. IDE-run uvicorn, background workers).
_ROOT = Path(__file__).resolve().parents[3]
if (_ROOT / ".env").is_file():
    load_dotenv(_ROOT / ".env", override=True)
load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str = DEFAULT_OPENAI_MODEL
    max_search_results: int = DEFAULT_MAX_SEARCH_RESULTS
    serpapi_key: str = ""
    geoapify_api_key: str = ""
    geoapify_dining_radius_m: int = DEFAULT_GEOAPIFY_DINING_RADIUS_M
    dining_max_results: int = DEFAULT_DINING_MAX_RESULTS
    flight_departure_id: str = DEFAULT_DEPARTURE_ID
    flight_arrival_id: str = DEFAULT_ARRIVAL_ID
    flight_max_results: int = DEFAULT_FLIGHT_MAX_RESULTS
    ticketmaster_api_key: str = ""
    show_max_results: int = DEFAULT_SHOW_MAX_RESULTS

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required.")

        model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
        max_results_raw = os.getenv("MAX_SEARCH_RESULTS", str(DEFAULT_MAX_SEARCH_RESULTS)).strip()
        max_results = int(max_results_raw) if max_results_raw.isdigit() else DEFAULT_MAX_SEARCH_RESULTS
        max_results = max(MIN_MAX_SEARCH_RESULTS, min(max_results, MAX_MAX_SEARCH_RESULTS))

        radius_raw = os.getenv("GEOAPIFY_DINING_RADIUS_M", str(DEFAULT_GEOAPIFY_DINING_RADIUS_M)).strip()
        geo_radius = int(radius_raw) if radius_raw.isdigit() else DEFAULT_GEOAPIFY_DINING_RADIUS_M
        geo_radius = max(MIN_GEOAPIFY_DINING_RADIUS_M, min(geo_radius, MAX_GEOAPIFY_DINING_RADIUS_M))

        dining_raw = os.getenv("DINING_MAX_RESULTS", str(DEFAULT_DINING_MAX_RESULTS)).strip()
        dining_max = int(dining_raw) if dining_raw.isdigit() else DEFAULT_DINING_MAX_RESULTS
        dining_max = max(MIN_DINING_MAX_RESULTS, min(dining_max, MAX_DINING_MAX_RESULTS))

        flight_max_raw = os.getenv("FLIGHT_MAX_RESULTS", str(DEFAULT_FLIGHT_MAX_RESULTS)).strip()
        flight_max = int(flight_max_raw) if flight_max_raw.isdigit() else DEFAULT_FLIGHT_MAX_RESULTS
        flight_max = max(MIN_FLIGHT_MAX_RESULTS, min(flight_max, MAX_FLIGHT_MAX_RESULTS))
        show_max_raw = os.getenv("SHOW_MAX_RESULTS", str(DEFAULT_SHOW_MAX_RESULTS)).strip()
        show_max = int(show_max_raw) if show_max_raw.isdigit() else DEFAULT_SHOW_MAX_RESULTS
        show_max = max(MIN_SHOW_MAX_RESULTS, min(show_max, MAX_SHOW_MAX_RESULTS))
        env_dep = normalize_us_iata(os.getenv("FLIGHT_DEPARTURE_ID", ""))
        env_arr = normalize_us_iata(os.getenv("FLIGHT_ARRIVAL_ID", ""))

        return cls(
            openai_api_key=api_key,
            openai_model=model,
            max_search_results=max_results,
            serpapi_key=os.getenv("SERPAPI_API_KEY", "").strip(),
            geoapify_api_key=os.getenv("GEOAPIFY_API_KEY", "").strip(),
            geoapify_dining_radius_m=geo_radius,
            dining_max_results=dining_max,
            flight_departure_id=env_dep or DEFAULT_DEPARTURE_ID,
            flight_arrival_id=env_arr or DEFAULT_ARRIVAL_ID,
            flight_max_results=flight_max,
            ticketmaster_api_key=os.getenv("TICKETMASTER_API_KEY", "").strip(),
            show_max_results=show_max,
        )
