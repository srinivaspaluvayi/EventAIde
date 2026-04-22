from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    max_search_results: int = 6

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required.")

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        max_results_raw = os.getenv("MAX_SEARCH_RESULTS", "6").strip()
        max_results = int(max_results_raw) if max_results_raw.isdigit() else 6
        max_results = max(3, min(max_results, 12))

        return cls(
            openai_api_key=api_key,
            openai_model=model,
            max_search_results=max_results,
        )

