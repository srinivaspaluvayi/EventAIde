from datetime import date, timedelta

from travel_planner.agents.preference_collector import PreferenceCollectorAgent


class _StubLLM:
    def __init__(self, payload=None, should_raise: bool = False) -> None:
        self.payload = payload or {}
        self.should_raise = should_raise

    def run_json(self, _system_prompt: str, _user_input: str, max_tokens: int = 0):  # noqa: ARG002
        if self.should_raise:
            raise RuntimeError("llm unavailable")
        return self.payload


def _safe_replace_year(value: date, year: int) -> date:
    try:
        return value.replace(year=year)
    except ValueError:
        return value.replace(year=year, day=28)


def test_stale_year_dates_are_shifted_to_upcoming_window() -> None:
    today = date.today()
    upcoming = today + timedelta(days=1)
    stale_start = _safe_replace_year(upcoming, upcoming.year - 2)
    stale_end = stale_start + timedelta(days=1)
    agent = PreferenceCollectorAgent(
        _StubLLM(
            payload={
                "destination": "Chicago",
                "start_date": str(stale_start),
                "end_date": str(stale_end),
            }
        )
    )

    profile = agent.run("plan 2 day trip from saint louis to chicago")

    assert profile.start_date >= today
    assert profile.end_date >= profile.start_date


def test_llm_relative_date_result_is_respected() -> None:
    today = date.today()
    tomorrow = today + timedelta(days=1)
    agent = PreferenceCollectorAgent(
        _StubLLM(
            payload={
                "destination": "Chicago",
                "start_date": str(tomorrow),
                "end_date": str(tomorrow + timedelta(days=2)),
            }
        )
    )

    profile = agent.run("plan 2 day trip from saint Louis to Chicago from tomorrow(23rd April)")

    assert profile.start_date == tomorrow
    assert profile.end_date == tomorrow + timedelta(days=2)

