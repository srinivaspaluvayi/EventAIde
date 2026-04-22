from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from travel_planner.config.settings import Settings
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


def main() -> None:
    st.set_page_config(page_title="AI Travel Planner", layout="wide")
    inject_custom_css()
    render_hero()
    st.caption("Agno + GPT-4o-mini + Streamlit")

    with st.container(border=True):
        st.markdown("### Tell us your travel preferences")
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
            settings = Settings.from_env()
            pipeline = TravelPlannerPipeline(settings=settings)
            plan = pipeline.run(user_input=user_prompt)
        except Exception as exc:
            st.error(f"Could not generate plan: {exc}")
            st.stop()

        st.success("Travel plan generated.")

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


if __name__ == "__main__":
    main()

