from __future__ import annotations

import os
from pathlib import Path
import sys

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from travel_planner.config.settings import Settings
from travel_planner.models.schemas import FinalPlan
from travel_planner.orchestration.pipeline import TravelPlannerPipeline
from travel_planner.ui.charts import build_budget_chart
from travel_planner.ui.components import (
    inject_custom_css,
    render_destination_insights,
    render_dining_picks,
    render_flights_picks,
    render_guided_setup_summary,
    render_hotels_picks,
    render_places_picks,
    render_scenario_summary,
    render_shows_picks,
    render_trip_scenarios,
    render_export_summary,
    render_hero,
    render_itinerary_browser,
    render_logistics,
    render_profile_summary,
    render_timeline_plan,
)
from travel_planner.utils.costing import (
    budget_summary_rows,
    estimated_total_spend_usd,
    flight_budget_options,
    itinerary_cost_table,
    selected_flight_context,
)


BACKEND_URL = os.getenv("TRIPFORGE_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def _request_plan(user_prompt: str) -> FinalPlan:
    response = requests.post(
        f"{BACKEND_URL}/v1/plan",
        json={"user_input": user_prompt},
        timeout=120,
    )
    if response.status_code != 200:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(detail)
    payload = response.json()
    return FinalPlan(**payload["plan"])


def _request_plan_with_fallback(user_prompt: str) -> FinalPlan:
    try:
        return _request_plan(user_prompt)
    except requests.RequestException:
        # Backend unavailable; gracefully fall back to in-process pipeline.
        settings = Settings.from_env()
        pipeline = TravelPlannerPipeline(settings=settings)
        return pipeline.run(user_input=user_prompt)


def main() -> None:
    st.set_page_config(page_title="TripForge AI", layout="wide")
    inject_custom_css()
    render_hero()
    st.caption("Plan smarter trips with provider-backed context and timeline-first execution.")

    if "generated_plan" not in st.session_state:
        st.session_state.generated_plan = None
    if "selected_flight_idx" not in st.session_state:
        st.session_state.selected_flight_idx = 0

    st.markdown(
        """
        <div class="landing-shell">
            <h3 class="landing-title">Start Your Trip Story</h3>
            <p class="landing-sub">Describe your trip in plain language. Include where, when, budget, style, and interests.</p>
            <div class="prompt-tips">
                <span class="prompt-tip">Route: St Louis to Chicago</span>
                <span class="prompt-tip">Duration: 3-5 days</span>
                <span class="prompt-tip">Budget + interests</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top_left, top_right = st.columns([0.78, 0.22])
    with top_left:
        user_prompt = st.text_area(
            "Travel request",
            placeholder=(
                "Example: Plan a 4 day trip from Saint Louis to Chicago with a $2200 budget, "
                "balanced pace, and interests in food, architecture, and live shows."
            ),
            height=140,
            label_visibility="collapsed",
        )
    with top_right:
        st.markdown(" ")
        if st.button("Generate Plan", type="primary", use_container_width=True):
            st.session_state._generate_clicked = True
        if st.button("Clear current plan", use_container_width=True):
            st.session_state.generated_plan = None
            st.session_state.selected_flight_idx = 0
            st.success("Cleared current plan.")
            st.rerun()

    if st.session_state.get("_generate_clicked"):
        st.session_state._generate_clicked = False
        if not user_prompt.strip():
            st.warning("Please provide your trip preferences.")
            st.stop()

        try:
            st.session_state.generated_plan = _request_plan_with_fallback(user_prompt)
            st.session_state.selected_flight_idx = 0
        except Exception as exc:
            st.error(f"Could not generate plan: {exc}")
            st.stop()

    plan = st.session_state.generated_plan
    if plan is not None:
        st.success("Travel plan generated. Use guided chapters below.")
        chapters = [
            "Plan Setup",
            "Trip Scenarios",
            "Execution Timeline",
            "Budget & Tradeoffs",
            "Export & Share",
        ]
        if "active_chapter" not in st.session_state:
            st.session_state.active_chapter = chapters[0]
        nav_cols = st.columns(len(chapters))
        for idx, name in enumerate(chapters):
            with nav_cols[idx]:
                active = st.session_state.active_chapter == name
                label = f"{'● ' if active else ''}{name}"
                if st.button(label, key=f"chapter_nav_{idx}", use_container_width=True):
                    st.session_state.active_chapter = name
        chapter = st.session_state.active_chapter

        if chapter == "Plan Setup":
            render_guided_setup_summary(user_prompt)
            st.divider()
            render_profile_summary(plan)
            st.divider()
            render_destination_insights(plan)
            st.divider()
            render_scenario_summary(plan)

        elif chapter == "Trip Scenarios":
            render_trip_scenarios(plan)
            st.divider()
            render_flights_picks(plan)
            st.divider()
            render_hotels_picks(plan)
            st.divider()
            render_places_picks(plan)
            st.divider()
            render_shows_picks(plan)
            st.divider()
            render_dining_picks(plan)

        elif chapter == "Execution Timeline":
            selected_idx = render_timeline_plan(plan, selected_flight_idx=st.session_state.selected_flight_idx)
            if selected_idx is not None:
                st.session_state.selected_flight_idx = selected_idx
            st.divider()
            render_itinerary_browser(plan)
            st.divider()
            render_logistics(plan)

        elif chapter == "Budget & Tradeoffs":
            st.subheader("Budget Breakdown")
            selected_flight_label, selected_flight_cost = selected_flight_context(
                plan, st.session_state.selected_flight_idx
            )
            flight_options = flight_budget_options(plan.flights or [])
            if flight_options:
                safe_idx = (
                    st.session_state.selected_flight_idx
                    if 0 <= st.session_state.selected_flight_idx < len(flight_options)
                    else 0
                )
                st.caption(f"Budget assumption uses {flight_options[safe_idx][0]}.")
            st.metric(
                "Estimated Total (including flights)",
                f"${estimated_total_spend_usd(plan, selected_flight_cost=selected_flight_cost):,.2f}",
            )
            st.table(
                budget_summary_rows(
                    plan,
                    selected_flight_cost=selected_flight_cost,
                    flight_label=selected_flight_label,
                )
            )
            st.caption("Top-line estimate includes itinerary activities plus the selected flight option.")
            if plan.budget_plan and plan.budget_plan.optimization_tips:
                st.markdown("#### Tradeoff recommendations")
                for tip in plan.budget_plan.optimization_tips[:5]:
                    st.markdown(f"- {tip}")
            st.divider()
            st.markdown("#### Day-by-day itinerary costs")
            st.table(itinerary_cost_table(plan.itinerary))
            st.pyplot(build_budget_chart(plan.itinerary), use_container_width=True)
            st.caption("Chart and table values are estimated from itinerary activities.")
        else:
            render_export_summary(plan, selected_flight_idx=st.session_state.selected_flight_idx)
            html_file = Path(plan.html_path)
            if html_file.exists():
                st.download_button(
                    label="Download HTML Travel Plan",
                    data=html_file.read_text(encoding="utf-8"),
                    file_name="travel_plan.html",
                    mime="text/html",
                )
                st.caption("The downloaded file includes print-friendly styling and day-by-day timeline sections.")


if __name__ == "__main__":
    main()

