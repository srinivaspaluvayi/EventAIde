from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from typing import Any, Dict, List

from travel_planner.models.schemas import TravelProfile
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Agent 1 (Preference Collector).
Mission: convert free-form travel intent into a complete structured profile.

Workflow:
1) Extract core fields:
- destination
- start/end dates
- budget
- travel style
- interests
- group size
2) Normalize values:
- dates in YYYY-MM-DD
- budget numeric in USD
- interests as clean list tokens
3) Identify missing/ambiguous fields and ask targeted clarifying questions.

Clarifying question policy:
- ask only high-impact questions
- keep questions short and specific
- avoid asking for information already explicit in input

Output policy:
- JSON only
- no markdown
- return exactly these keys:
destination, start_date, end_date, budget_usd, travel_style, interests, group_size, clarifying_questions
"""


class PreferenceCollectorAgent:
    def __init__(self, llm: SmallModelClient) -> None:
        self.llm = llm

    def run(self, user_input: str) -> TravelProfile:
        today = date.today()
        inferred_budget = self._extract_budget_from_text(user_input)
        fallback = {
            "destination": "Tokyo",
            "start_date": str(today + timedelta(days=30)),
            "end_date": str(today + timedelta(days=34)),
            "budget_usd": inferred_budget if inferred_budget is not None else 2200,
            "travel_style": "balanced",
            "interests": ["food", "culture"],
            "group_size": 1,
            "clarifying_questions": [],
        }
        try:
            parsed = self.llm.run_json(SYSTEM_PROMPT, user_input, max_tokens=420)
        except Exception:
            parsed = fallback
        normalized = self._normalize_profile_payload(parsed, fallback)
        return TravelProfile(**normalized)

    def _normalize_profile_payload(self, parsed: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        payload = {**fallback}
        if not isinstance(parsed, dict):
            return payload

        for key in ("destination", "travel_style"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                payload[key] = value.strip()

        for key in ("start_date", "end_date"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                payload[key] = self._normalize_date_str(value.strip(), fallback[key])

        budget_value = parsed.get("budget_usd")
        if isinstance(budget_value, (int, float)) and budget_value > 0:
            payload["budget_usd"] = float(budget_value)
        elif isinstance(budget_value, str):
            cleaned = "".join(ch for ch in budget_value if ch.isdigit() or ch == ".")
            try:
                amount = float(cleaned)
                if amount > 0:
                    payload["budget_usd"] = amount
            except Exception:
                pass

        group_size = parsed.get("group_size")
        if isinstance(group_size, int) and group_size >= 1:
            payload["group_size"] = min(group_size, 20)
        elif isinstance(group_size, str) and group_size.isdigit():
            payload["group_size"] = min(max(int(group_size), 1), 20)

        interests = parsed.get("interests")
        if isinstance(interests, list):
            cleaned_interests = [str(item).strip() for item in interests if str(item).strip()]
            if cleaned_interests:
                payload["interests"] = cleaned_interests[:8]
        elif isinstance(interests, str) and interests.strip():
            payload["interests"] = [part.strip() for part in interests.split(",") if part.strip()][:8] or payload["interests"]

        clarifying = parsed.get("clarifying_questions")
        payload["clarifying_questions"] = self._normalize_clarifying_questions(clarifying)
        return payload

    def _normalize_clarifying_questions(self, clarifying: Any) -> List[str]:
        if isinstance(clarifying, list):
            return [str(item).strip() for item in clarifying if str(item).strip()][:6]
        if isinstance(clarifying, dict):
            questions: List[str] = []
            for value in clarifying.values():
                if isinstance(value, str) and value.strip():
                    questions.append(value.strip())
            return questions[:6]
        if isinstance(clarifying, str) and clarifying.strip():
            return [clarifying.strip()]
        return []

    def _normalize_date_str(self, value: str, fallback_date: str) -> str:
        candidate = value[:10]
        try:
            parsed = datetime.strptime(candidate, "%Y-%m-%d").date()
            return str(parsed)
        except Exception:
            return fallback_date

    def _extract_budget_from_text(self, text: str) -> float | None:
        raw = (text or "").lower()
        if not raw.strip():
            return None

        # Matches patterns like "$1500", "1500 usd", "budget 2k", "under 1.8k"
        match = re.search(
            r"(?:\$|usd\s*|budget\s*(?:is|of|under|around|about)?\s*)?(\d+(?:\.\d+)?)\s*(k|usd)?",
            raw,
        )
        if not match:
            return None

        value = float(match.group(1))
        suffix = match.group(2) or ""
        if suffix == "k":
            value *= 1000

        if 100 <= value <= 100000:
            return round(value, 2)
        return None

