from __future__ import annotations

import streamlit as st

from travel_planner.models.schemas import FinalPlan


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        .hero-card {
            background: linear-gradient(120deg, #0f172a 0%, #1d4ed8 100%);
            border-radius: 16px;
            padding: 1.2rem 1.4rem;
            color: #ffffff;
            margin-bottom: 1rem;
        }
        .metric-card {
            border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 12px;
            padding: 0.85rem 1rem;
            background: rgba(250, 250, 250, 0.03);
            margin-bottom: 0.5rem;
        }
        .badge {
            display: inline-block;
            background: #eef2ff;
            color: #1e3a8a;
            border-radius: 999px;
            padding: 0.25rem 0.65rem;
            margin: 0.12rem 0.2rem 0.12rem 0;
            font-size: 0.82rem;
            font-weight: 600;
        }
        .activity-card {
            border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 12px;
            padding: 0.8rem 0.9rem;
            margin-bottom: 0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <h2 style="margin:0;">Multi-Agent AI Travel Planner</h2>
            <p style="margin:0.4rem 0 0 0;">
                Personalized itinerary generation with destination research, logistics planning, and budget tracking.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_summary(plan: FinalPlan) -> None:
    profile = plan.profile
    trip_days = (profile.end_date - profile.start_date).days + 1
    metric_cols = st.columns(4)
    metric_cols[0].metric("Destination", profile.destination)
    metric_cols[1].metric("Trip Length", f"{trip_days} days")
    metric_cols[2].metric("Budget", f"${profile.budget_usd:,.0f}")
    metric_cols[3].metric("Group Size", str(profile.group_size))

    st.markdown("### Traveler Preferences")
    st.markdown(
        f"""
        <div class="metric-card"><b>Travel Style:</b> {profile.travel_style.title()}</div>
        <div class="metric-card"><b>Dates:</b> {profile.start_date} to {profile.end_date}</div>
        """,
        unsafe_allow_html=True,
    )
    interests = "".join([f'<span class="badge">{interest}</span>' for interest in profile.interests])
    st.markdown(interests, unsafe_allow_html=True)

    if profile.clarifying_questions:
        st.info("Clarifying questions that can improve the plan:")
        for question in profile.clarifying_questions:
            st.write(f"- {question}")


def render_destination_insights(plan: FinalPlan) -> None:
    info = plan.destination_info
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Highlights")
        for item in info.highlights:
            st.write(f"- {item}")
        st.markdown("### Best Areas To Stay")
        for item in info.best_areas_to_stay:
            st.write(f"- {item}")
    with col2:
        st.markdown("### Local Tips")
        for item in info.local_tips:
            st.write(f"- {item}")
        st.markdown("### Travel Essentials")
        st.write(f"**Visa:** {info.visa_requirements}")
        st.write(f"**Weather:** {info.weather_summary}")


def render_itinerary_browser(plan: FinalPlan) -> None:
    st.subheader("Day-by-Day Itinerary")
    day_map = {f"Day {day.day}": day for day in plan.itinerary.days}
    selected = st.selectbox("Choose a day", options=list(day_map.keys()))
    day = day_map[selected]

    st.markdown(f"#### {selected}  |  Total: ${day.day_total_usd:.2f}")
    for label, activity in (
        ("Morning", day.morning),
        ("Afternoon", day.afternoon),
        ("Evening", day.evening),
    ):
        st.markdown(
            f"""
            <div class="activity-card">
                <b>{label}:</b> {activity.title}<br/>
                <span style="color:#475569;">{activity.details}</span><br/>
                <b>Estimated Cost:</b> ${activity.estimated_cost_usd:.2f}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_itinerary_timeline(plan: FinalPlan) -> None:
    st.markdown("#### Full Timeline")
    for day in plan.itinerary.days:
        with st.expander(f"Day {day.day} - ${day.day_total_usd:.2f}", expanded=False):
            st.markdown(f"**Morning:** {day.morning.title} · `${day.morning.estimated_cost_usd:.2f}`")
            st.caption(day.morning.details)
            st.markdown(f"**Afternoon:** {day.afternoon.title} · `${day.afternoon.estimated_cost_usd:.2f}`")
            st.caption(day.afternoon.details)
            st.markdown(f"**Evening:** {day.evening.title} · `${day.evening.estimated_cost_usd:.2f}`")
            st.caption(day.evening.details)


def render_logistics(plan: FinalPlan) -> None:
    logistics = plan.logistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### Stay")
        for item in logistics.accommodation_options:
            st.write(f"- {item}")
    with col2:
        st.markdown("### Transport")
        for item in logistics.local_transport:
            st.write(f"- {item}")
    with col3:
        st.markdown("### Packing")
        for item in logistics.packing_tips:
            st.write(f"- {item}")


def render_export_summary(plan: FinalPlan) -> None:
    profile = plan.profile
    days = (profile.end_date - profile.start_date).days + 1
    st.success(
        f"Ready to export: {profile.destination} | {days} days | "
        f"Estimated spend ${plan.itinerary.estimated_total_usd:,.2f}"
    )

