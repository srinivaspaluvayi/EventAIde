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
    render_export_summary,
    render_hero,
    render_itinerary_browser,
    render_itinerary_timeline,
    render_logistics,
    render_profile_summary,
)
from travel_planner.utils.costing import itinerary_cost_table


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
    st.caption("TripForge AI · Agno + GPT-4o-mini + Streamlit")

    if "generated_plan" not in st.session_state:
        st.session_state.generated_plan = None

    with st.container(border=True):
        top_left, top_right = st.columns([0.8, 0.2])
        with top_left:
            st.markdown("### Tell us your travel preferences")
        with top_right:
            if st.button("Clear current plan", use_container_width=True):
                st.session_state.generated_plan = None
                st.success("Cleared current plan.")
                st.rerun()
        st.caption("Include destination, date range, budget, travel style, interests, and group size for best results.")
        user_prompt = st.text_area(
            "Travel request",
            placeholder=(
                "Example: Plan a 5-day Tokyo trip in October with a $1800 budget "
                "for food and anime spots."
            ),
            height=130,
            label_visibility="collapsed",
        )

    if st.button("Generate Plan", type="primary"):
        if not user_prompt.strip():
            st.warning("Please provide your trip preferences.")
            st.stop()

        try:
            st.session_state.generated_plan = _request_plan_with_fallback(user_prompt)
        except Exception as exc:
            st.error(f"Could not generate plan: {exc}")
            st.stop()

    plan = st.session_state.generated_plan
    if plan is not None:
        st.success("Travel plan generated. Explore each tab below to review and export.")

        tab_overview, tab_itinerary, tab_logistics, tab_budget, tab_export = st.tabs(
            ["Overview", "Itinerary", "Logistics", "Budget", "Export"]
        )

        with tab_overview:
            render_profile_summary(plan)
            st.divider()
            render_destination_insights(plan)

        with tab_itinerary:
            render_itinerary_browser(plan)
            st.divider()
            render_itinerary_timeline(plan)

        with tab_logistics:
            render_logistics(plan)

        with tab_budget:
            st.subheader("Budget Breakdown")
            st.table(itinerary_cost_table(plan.itinerary))
            st.pyplot(build_budget_chart(plan.itinerary), use_container_width=True)
            st.caption("Chart and table values are estimated from itinerary activities.")

        with tab_export:
            render_export_summary(plan)
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

