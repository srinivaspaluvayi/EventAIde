from __future__ import annotations

import html
import streamlit as st

from travel_planner.models.schemas import FinalPlan, FlightOption, FoodOption


def _dining_row_source(notes: str) -> str:
    n = notes or ""
    if "[source:provider:geoapify]" in n:
        return "Geoapify"
    if "[source:fallback:llm]" in n:
        return "LLM fallback"
    return "Unknown"


def _dining_plan_summary(dining: list[FoodOption]) -> str:
    if not dining:
        return "No dining rows returned."
    geo = sum(1 for d in dining if "[source:provider:geoapify]" in (d.notes or ""))
    llm = sum(1 for d in dining if "[source:fallback:llm]" in (d.notes or ""))
    if llm == 0:
        return f"All **{len(dining)}** picks are **Geoapify** POI data (not LLM-invented venues)."
    if geo == 0:
        return f"All **{len(dining)}** picks are **LLM fallback** (Geoapify unavailable or returned no rows)."
    return f"**Mixed:** {geo} from Geoapify, {llm} from LLM fallback."


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        :root,
        html[data-theme="light"],
        .stApp[data-theme="light"] {
            --bg-soft: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #475569;
            --brand-500: #2563eb;
            --brand-700: #1d4ed8;
            --line-soft: rgba(148, 163, 184, 0.35);
            --hero-fg: #ffffff;
            --chip-bg: #eef2ff;
            --chip-fg: #1e3a8a;
        }
        html[data-theme="dark"],
        .stApp[data-theme="dark"] {
            --bg-soft: #0b1220;
            --card-bg: #111827;
            --text-main: #e2e8f0;
            --text-muted: #94a3b8;
            --brand-500: #60a5fa;
            --brand-700: #3b82f6;
            --line-soft: rgba(148, 163, 184, 0.3);
            --hero-fg: #f8fafc;
            --chip-bg: rgba(59, 130, 246, 0.2);
            --chip-fg: #bfdbfe;
        }
        .block-container {
            padding-top: 1.5rem;
        }
        .hero-card {
            background: radial-gradient(circle at top left, #1d4ed8 0%, #0f172a 55%);
            border-radius: 18px;
            padding: 1.25rem 1.4rem;
            color: var(--hero-fg);
            margin-bottom: 1rem;
            box-shadow: 0 14px 32px rgba(15, 23, 42, 0.22);
        }
        .hero-sub {
            opacity: 0.92;
            margin-top: 0.45rem;
        }
        .flow-row {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-top: 0.6rem;
        }
        .flow-pill {
            font-size: 0.76rem;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.2);
        }
        .metric-card {
            border: 1px solid var(--line-soft);
            border-radius: 12px;
            padding: 0.85rem 1rem;
            background: var(--bg-soft);
            margin-bottom: 0.5rem;
            color: var(--text-main);
        }
        .badge {
            display: inline-block;
            background: var(--chip-bg);
            color: var(--chip-fg);
            border-radius: 999px;
            padding: 0.25rem 0.65rem;
            margin: 0.12rem 0.2rem 0.12rem 0;
            font-size: 0.82rem;
            font-weight: 600;
        }
        .section-title {
            margin-top: 0.25rem;
            margin-bottom: 0.4rem;
            color: var(--text-main);
        }
        .card-panel {
            border: 1px solid var(--line-soft);
            background: var(--card-bg);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.65rem;
        }
        .card-panel, .card-panel * {
            color: var(--text-main) !important;
        }
        .activity-card {
            border: 1px solid var(--line-soft);
            border-radius: 12px;
            padding: 0.8rem 0.95rem;
            margin-bottom: 0.6rem;
            background: var(--card-bg);
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        }
        .activity-card, .activity-card * {
            color: var(--text-main) !important;
        }
        .activity-detail {
            color: var(--text-muted) !important;
        }
        .cost-badge {
            display: inline-block;
            margin-top: 0.4rem;
            padding: 0.18rem 0.55rem;
            border-radius: 999px;
            background: var(--chip-bg);
            color: var(--chip-fg) !important;
            font-weight: 700;
            font-size: 0.76rem;
        }
        .subtle-note {
            color: var(--text-muted);
            font-size: 0.86rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <h2 style="margin:0;">TripForge AI</h2>
            <p class="hero-sub">
                Intelligent trip planning that turns rough travel ideas into polished, day-by-day journeys.
            </p>
            <div class="flow-row">
                <span class="flow-pill">Preferences</span>
                <span class="flow-pill">Research</span>
                <span class="flow-pill">Itinerary</span>
                <span class="flow-pill">Logistics</span>
                <span class="flow-pill">Export</span>
            </div>
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
            st.markdown(f'<div class="card-panel">• {item}</div>', unsafe_allow_html=True)
        st.markdown("### Best Areas To Stay")
        for item in info.best_areas_to_stay:
            st.markdown(f'<div class="card-panel">• {item}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("### Local Tips")
        for item in info.local_tips:
            st.markdown(f'<div class="card-panel">• {item}</div>', unsafe_allow_html=True)
        st.markdown("### Travel Essentials")
        st.markdown(f'<div class="card-panel"><b>Visa:</b> {info.visa_requirements}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-panel"><b>Weather:</b> {info.weather_summary}</div>', unsafe_allow_html=True)


def _flight_row_source(notes: str) -> str:
    n = notes or ""
    if "[source:provider:serpapi]" in n:
        return "SerpAPI"
    if "[source:fallback:llm]" in n:
        return "LLM fallback"
    return "Unknown"


def _flight_plan_summary(flights: list[FlightOption]) -> str:
    if not flights:
        return "No flight rows returned."
    serp = sum(1 for f in flights if "[source:provider:serpapi]" in (f.notes or ""))
    llm = sum(1 for f in flights if "[source:fallback:llm]" in (f.notes or ""))
    if llm == 0 and serp > 0:
        return f"All **{len(flights)}** options are **SerpAPI / Google Flights** estimates."
    if serp == 0:
        return f"All **{len(flights)}** options are **LLM fallback** (SerpAPI flights not configured or no results)."
    return f"**Mixed:** {serp} SerpAPI, {llm} LLM fallback."


def render_flights_picks(plan: FinalPlan) -> None:
    st.markdown("### Flight options")
    flights = plan.flights or []
    st.markdown(_flight_plan_summary(flights))
    if not flights:
        st.caption("Set `SERPAPI_API_KEY`, `FLIGHT_DEPARTURE_ID`, and `FLIGHT_ARRIVAL_ID` (or IATA in destination) for live Google Flights bundles.")
        return
    for idx, f in enumerate(flights, start=1):
        src = _flight_row_source(f.notes or "")
        badge_class = "badge" if src == "SerpAPI" else "cost-badge"
        route = html.escape(f.route)
        airline = html.escape(f.airline)
        notes = html.escape(f.notes or "")
        src_e = html.escape(src)
        st.markdown(
            f"""
            <div class="activity-card">
                <b>{idx}. {route}</b>
                <span class="{badge_class}" style="margin-left:0.35rem;">{src_e}</span><br/>
                <span class="activity-detail">{airline} · est. ${f.estimated_cost_usd:,.0f}</span><br/>
                <span class="activity-detail">{notes}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_dining_picks(plan: FinalPlan) -> None:
    """Show full dining list from ``plan.dining`` (Geoapify or LLM) — itinerary tab alone stays generic."""
    st.markdown("### Dining picks")
    dining = plan.dining or []
    st.markdown(_dining_plan_summary(dining))
    if not dining:
        st.caption("Enable `GEOAPIFY_API_KEY` and regenerate to load OSM-backed restaurants.")
        return
    for idx, d in enumerate(dining, start=1):
        src = _dining_row_source(d.notes or "")
        badge_class = "badge" if src == "Geoapify" else "cost-badge"
        name = html.escape(d.name)
        cuisine = html.escape(d.cuisine)
        price = html.escape(d.price_level)
        notes = html.escape(d.notes or "")
        src_e = html.escape(src)
        st.markdown(
            f"""
            <div class="activity-card">
                <b>{idx}. {name}</b>
                <span class="{badge_class}" style="margin-left:0.35rem;">{src_e}</span><br/>
                <span class="activity-detail">{cuisine} · {price}</span><br/>
                <span class="activity-detail">{notes}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_itinerary_browser(plan: FinalPlan) -> None:
    st.subheader("Day-by-Day Itinerary")
    day_map = {f"Day {day.day}": day for day in plan.itinerary.days}
    selected = st.selectbox("Choose a day focus", options=list(day_map.keys()))
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
                <span class="activity-detail">{activity.details}</span><br/>
                <span class="cost-badge">Estimated ${activity.estimated_cost_usd:.2f}</span>
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
            st.markdown(f'<div class="card-panel">• {item}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("### Transport")
        for item in logistics.local_transport:
            st.markdown(f'<div class="card-panel">• {item}</div>', unsafe_allow_html=True)
    with col3:
        st.markdown("### Packing")
        for item in logistics.packing_tips:
            st.markdown(f'<div class="card-panel">• {item}</div>', unsafe_allow_html=True)


def render_export_summary(plan: FinalPlan) -> None:
    profile = plan.profile
    days = (profile.end_date - profile.start_date).days + 1
    st.success(
        f"Ready to export: {profile.destination} | {days} days | "
        f"Estimated spend ${plan.itinerary.estimated_total_usd:,.2f}"
    )
    st.markdown(
        '<p class="subtle-note">Export your TripForge AI report to share with recruiters, interviewers, clients, or travel partners.</p>',
        unsafe_allow_html=True,
    )

