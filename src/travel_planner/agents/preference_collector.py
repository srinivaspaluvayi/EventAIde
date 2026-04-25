from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from typing import Any, Dict, List

from travel_planner.config.defaults import (
    DEFAULT_ARRIVAL_ID,
    DEFAULT_BUDGET_USD,
    DEFAULT_DEPARTURE_ID,
    DEFAULT_DESTINATION,
    DEFAULT_GROUP_SIZE,
    DEFAULT_INTERESTS,
    DEFAULT_TRAVEL_STYLE,
    DEFAULT_TRIP_DAYS,
)
from travel_planner.models.schemas import TravelProfile
from travel_planner.utils.us_airports import normalize_us_iata
from travel_planner.utils.llm import SmallModelClient


SYSTEM_PROMPT = """
You are Agent 1 (Preference Collector).
Goal: extract every usable travel preference from the user text into a strict profile JSON.

Input format:
- You receive:
  - `Today: YYYY-MM-DD`
  - `User request: ...`

Extraction requirements (high priority):
1) Capture all explicit details from the user request:
   - destination
   - start_date / end_date
   - budget_usd
   - travel_style
   - interests
   - group_size
   - departure_id / arrival_id (US 3-letter IATA only when explicitly present)
2) Preserve user intent wording where possible; do not overwrite clear user constraints.
3) If a field is missing, leave it empty/null-like in your internal reasoning rather than inventing specifics.

Date rules:
- Resolve relative dates against `Today` (e.g., "tomorrow", "next Friday", "23rd April").
- Prefer upcoming/future interpretation.
- Never choose a past year if a future date interpretation is plausible.
- Output dates only in `YYYY-MM-DD` format.

Group size rules:
- If user clearly states party size, set it.
- If not clearly stated, set `group_size` to 1.

Clarifying questions:
- Add only high-impact unresolved questions.
- Keep questions short and specific.
- Do not ask about information that is already explicit.

Output rules:
- Return JSON only (no markdown, no extra keys).
- Return exactly these keys:
  destination, start_date, end_date, budget_usd, travel_style, interests, group_size, departure_id, arrival_id, clarifying_questions
"""


class PreferenceCollectorAgent:
    def __init__(self, llm: SmallModelClient) -> None:
        self.llm = llm

    def run(self, user_input: str) -> TravelProfile:
        today = date.today()
        inferred_budget = self._extract_budget_from_text(user_input)
        hinted_days = self._extract_trip_days_hint(user_input)
        span_days = hinted_days if hinted_days is not None else DEFAULT_TRIP_DAYS
        explicit_end = self._extract_iso_date_from_text(user_input)
        default_start = today
        default_end = explicit_end if explicit_end is not None else (default_start + timedelta(days=span_days))
        fallback = {
            "destination": DEFAULT_DESTINATION,
            "start_date": str(default_start),
            "end_date": str(default_end),
            "budget_usd": inferred_budget if inferred_budget is not None else DEFAULT_BUDGET_USD,
            "travel_style": DEFAULT_TRAVEL_STYLE,
            "interests": DEFAULT_INTERESTS,
            "group_size": DEFAULT_GROUP_SIZE,
            "departure_id": DEFAULT_DEPARTURE_ID,
            "arrival_id": DEFAULT_ARRIVAL_ID,
            "clarifying_questions": [],
        }
        llm_input = f"Today: {today.isoformat()}\nUser request: {user_input}"
        try:
            parsed = self.llm.run_json(SYSTEM_PROMPT, llm_input, max_tokens=420)
        except Exception:
            parsed = fallback
        normalized = self._normalize_profile_payload(
            parsed,
            fallback,
            today,
            span_days,
            enforce_hinted_span=hinted_days is not None,
        )
        return TravelProfile(**normalized)

    def _normalize_profile_payload(
        self,
        parsed: Dict[str, Any],
        fallback: Dict[str, Any],
        today: date,
        default_span_days: int,
        enforce_hinted_span: bool = False,
    ) -> Dict[str, Any]:
        payload = {**fallback}
        if not isinstance(parsed, dict):
            return payload

        for key in ("destination", "travel_style"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                payload[key] = value.strip()

        start_d = self._parse_iso_date(parsed.get("start_date"))
        end_d = self._parse_iso_date(parsed.get("end_date"))
        start_d, end_d = self._resolve_trip_dates(start_d, end_d, today, default_span_days)
        if enforce_hinted_span:
            min_end = start_d + timedelta(days=max(1, default_span_days))
            if end_d < min_end:
                end_d = min_end
        payload["start_date"] = str(start_d)
        payload["end_date"] = str(end_d)

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
        elif isinstance(group_size, str) and group_size.strip().isdigit():
            payload["group_size"] = min(max(int(group_size.strip()), 1), 20)
        else:
            payload["group_size"] = DEFAULT_GROUP_SIZE

        dep = self._normalize_iata_code(parsed.get("departure_id"))
        arr = self._normalize_iata_code(parsed.get("arrival_id"))
        payload["departure_id"] = dep or fallback["departure_id"]
        payload["arrival_id"] = arr or fallback["arrival_id"]

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

    def _normalize_iata_code(self, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        text = value.strip().upper()
        return normalize_us_iata(text)

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

    def _parse_iso_date(self, value: Any) -> date | None:
        if not isinstance(value, str) or not value.strip():
            return None
        candidate = value.strip()[:10]
        try:
            return datetime.strptime(candidate, "%Y-%m-%d").date()
        except Exception:
            return None

    def _resolve_trip_dates(
        self, start_d: date | None, end_d: date | None, today: date, default_span_days: int
    ) -> tuple[date, date]:
        """Default outbound to today when missing; default trip length 7 nights when end missing."""
        default_span = timedelta(days=max(1, default_span_days))
        if start_d is not None:
            start_d = self._coerce_to_upcoming_date(start_d, today)
        if end_d is not None:
            end_d = self._coerce_to_upcoming_date(end_d, today)
        if start_d is None and end_d is None:
            return today, today + default_span
        if start_d is None:
            start_d = today
            if end_d is None:
                return start_d, start_d + default_span
            if end_d < start_d:
                end_d = start_d + default_span
            return start_d, end_d
        if end_d is None:
            return start_d, start_d + default_span
        if end_d < start_d:
            end_d = start_d + timedelta(days=1)
        return start_d, end_d

    def _coerce_to_upcoming_date(self, value: date, today: date) -> date:
        """Shift obviously stale years forward to the next sensible upcoming date."""
        if value >= today:
            return value
        bumped = value
        # Keep month/day but roll year forward until today or later.
        while bumped < today and bumped.year < today.year + 5:
            try:
                bumped = bumped.replace(year=bumped.year + 1)
            except ValueError:
                # Feb 29 on non-leap year -> move to Feb 28.
                bumped = bumped.replace(year=bumped.year + 1, day=28)
        return bumped

    def _extract_trip_days_hint(self, text: str) -> int | None:
        raw = (text or "").lower()
        m = re.search(r"\b(\d{1,2})\s*day(?:s)?\b", raw)
        if not m:
            return None
        try:
            days = int(m.group(1))
            return max(1, min(days, 30))
        except Exception:
            return None

    def _extract_iso_date_from_text(self, text: str) -> date | None:
        raw = text or ""
        m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", raw)
        if not m:
            return None
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except Exception:
            return None

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

