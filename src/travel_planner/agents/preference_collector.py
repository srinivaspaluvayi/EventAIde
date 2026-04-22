from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from travel_planner.models.schemas import TravelProfile
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Agent 1 (Preference Collector).
Extract travel preferences into strict JSON.
If data is missing, add concise clarifying questions.
Return JSON only with keys:
destination, start_date, end_date, budget_usd, travel_style, interests, group_size, clarifying_questions
Dates must be ISO format YYYY-MM-DD.
"""


class PreferenceCollectorAgent:
    def __init__(self, llm: SmallModelClient) -> None:
        self.llm = llm

    def run(self, user_input: str) -> TravelProfile:
        today = date.today()
        fallback = {
            "destination": "Tokyo",
            "start_date": str(today + timedelta(days=30)),
            "end_date": str(today + timedelta(days=34)),
            "budget_usd": 1500,
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
                payload[key] = value.strip()

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

