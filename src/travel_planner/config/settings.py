from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Anchor .env to the project root (parent of `src/`) so API keys load even when the
# process cwd is not the repository (e.g. IDE-run uvicorn, background workers).
_ROOT = Path(__file__).resolve().parents[3]
if (_ROOT / ".env").is_file():
    load_dotenv(_ROOT / ".env", override=True)
load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    max_search_results: int = 6
    serpapi_key: str = ""
    geoapify_api_key: str = ""
    geoapify_dining_radius_m: int = 8000
    dining_max_results: int = 30
    flight_departure_id: str = ""
    flight_arrival_id: str = ""
    flight_max_results: int = 12

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required.")

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        max_results_raw = os.getenv("MAX_SEARCH_RESULTS", "6").strip()
        max_results = int(max_results_raw) if max_results_raw.isdigit() else 6
        max_results = max(3, min(max_results, 12))

        radius_raw = os.getenv("GEOAPIFY_DINING_RADIUS_M", "8000").strip()
        geo_radius = int(radius_raw) if radius_raw.isdigit() else 8000
        geo_radius = max(1000, min(geo_radius, 50_000))

        dining_raw = os.getenv("DINING_MAX_RESULTS", "30").strip()
        dining_max = int(dining_raw) if dining_raw.isdigit() else 30
        dining_max = max(5, min(dining_max, 100))

        flight_max_raw = os.getenv("FLIGHT_MAX_RESULTS", "12").strip()
        flight_max = int(flight_max_raw) if flight_max_raw.isdigit() else 12
        flight_max = max(5, min(flight_max, 25))

        return cls(
            openai_api_key=api_key,
            openai_model=model,
            max_search_results=max_results,
            serpapi_key=os.getenv("SERPAPI_API_KEY", "").strip(),
            geoapify_api_key=os.getenv("GEOAPIFY_API_KEY", "").strip(),
            geoapify_dining_radius_m=geo_radius,
            dining_max_results=dining_max,
            flight_departure_id=os.getenv("FLIGHT_DEPARTURE_ID", "").strip().upper(),
            flight_arrival_id=os.getenv("FLIGHT_ARRIVAL_ID", "").strip().upper(),
            flight_max_results=flight_max,
        )
