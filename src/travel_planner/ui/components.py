from __future__ import annotations

import html
import streamlit as st

from travel_planner.models.schemas import FinalPlan, FlightOption, FoodOption, HotelOption, PlaceOption, TimelineEntry
from travel_planner.utils.costing import (
    estimated_flight_cost_usd,
    estimated_total_spend_usd,
    flight_budget_options,
)


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
            background: linear-gradient(120deg, #1d4ed8 0%, #1e3a8a 48%, #0f172a 100%);
            border-radius: 20px;
            padding: 1.4rem 1.5rem;
            color: var(--hero-fg);
            margin-bottom: 1rem;
            box-shadow: 0 14px 32px rgba(15, 23, 42, 0.22);
            border: 1px solid rgba(191, 219, 254, 0.25);
        }
        .hero-title {
            margin: 0;
            font-size: 2rem;
            letter-spacing: 0.2px;
        }
        .hero-sub {
            opacity: 0.92;
            margin-top: 0.45rem;
            max-width: 60rem;
            line-height: 1.45;
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
        .hero-stats {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-top: 0.7rem;
        }
        .hero-stat {
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            background: rgba(15, 23, 42, 0.25);
            padding: 0.45rem 0.65rem;
            font-size: 0.8rem;
        }
        .landing-shell {
            border: 1px solid var(--line-soft);
            border-radius: 16px;
            background: var(--card-bg);
            padding: 1rem;
            margin-bottom: 0.9rem;
        }
        .landing-title {
            margin: 0;
            color: var(--text-main);
            font-size: 1.4rem;
        }
        .landing-sub {
            color: var(--text-muted);
            margin-top: 0.35rem;
            margin-bottom: 0;
            font-size: 0.92rem;
        }
        .prompt-tips {
            margin-top: 0.75rem;
            margin-bottom: 0.35rem;
        }
        .prompt-tip {
            display: inline-block;
            margin: 0.2rem 0.3rem 0.2rem 0;
            padding: 0.2rem 0.55rem;
            border-radius: 999px;
            border: 1px solid var(--line-soft);
            background: var(--bg-soft);
            color: var(--text-muted);
            font-size: 0.78rem;
        }
        .story-shell {
            border: 1px solid var(--line-soft);
            border-radius: 14px;
            background: var(--card-bg);
            padding: 0.9rem 1rem;
            margin-bottom: 0.8rem;
        }
        .story-shell-title {
            margin: 0;
            color: var(--text-main);
            font-size: 1.04rem;
            font-weight: 700;
        }
        .story-shell-sub {
            color: var(--text-muted);
            font-size: 0.86rem;
            margin-top: 0.25rem;
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
        .badge-provider {
            background: rgba(16, 185, 129, 0.2);
            color: #6ee7b7;
        }
        .badge-fallback {
            background: rgba(245, 158, 11, 0.2);
            color: #fcd34d;
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
            <h2 class="hero-title">TripForge AI</h2>
            <p class="hero-sub">
                Turn rough travel ideas into a complete trip narrative with real flight constraints, timed events,
                stay options, dining, and day-by-day execution.
            </p>
            <div class="hero-stats">
                <span class="hero-stat">Timeline-first scheduling</span>
                <span class="hero-stat">Flight-aware budgeting</span>
                <span class="hero-stat">Provider + fallback transparency</span>
            </div>
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


def render_story_shell(title: str, subtitle: str = "") -> None:
    subtitle_html = f'<div class="story-shell-sub">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="story-shell">
            <p class="story-shell-title">{html.escape(title)}</p>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scenario_summary(plan: FinalPlan) -> None:
    summary = plan.scenario_summary
    render_story_shell(
        "Scenario Confidence",
        "Provider and fallback mix across flights, stay, dining, places, and events.",
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flight scenarios", summary.scenario_count)
    c2.metric("Provider rows", summary.provider_flights + summary.provider_hotels + summary.provider_dining + summary.provider_places + summary.provider_shows)
    c3.metric("Fallback rows", summary.fallback_flights + summary.fallback_hotels + summary.fallback_dining + summary.fallback_places + summary.fallback_shows)
    c4.metric("Timeline mode", "Flight-driven" if summary.scenario_count else "Default")


def render_guided_setup_summary(user_prompt: str) -> None:
    render_story_shell("Plan Setup", "Capture preferences in plain language; we normalize and validate before agent orchestration.")
    if user_prompt.strip():
        st.caption("Prompt preview")
        st.code(user_prompt.strip(), language="text")


def render_trip_scenarios(plan: FinalPlan) -> None:
    render_story_shell("Trip Scenarios", "Each flight option is treated as a scenario with cost and timing assumptions.")
    if not plan.flights:
        st.caption("No flight scenarios available yet.")
        return
    cols = st.columns(min(len(plan.flights), 3))
    for idx, flight in enumerate(plan.flights[:3]):
        with cols[idx]:
            st.markdown(
                f"""
                <div class="activity-card">
                    <b>Scenario {idx+1}</b><br/>
                    <span class="activity-detail">{html.escape(flight.route)}</span><br/>
                    <span class="activity-detail">{html.escape(flight.airline)} · ${flight.estimated_cost_usd:,.0f}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_source_chips(provider_count: int, fallback_count: int, provider_name: str) -> None:
    chips = []
    if provider_count > 0:
        chips.append(f'<span class="badge badge-provider">{provider_name}: {provider_count}</span>')
    if fallback_count > 0:
        chips.append(f'<span class="badge badge-fallback">LLM fallback: {fallback_count}</span>')
    if chips:
        st.markdown("".join(chips), unsafe_allow_html=True)


def render_destination_insights(plan: FinalPlan) -> None:
    render_story_shell("Destination Chapter", "Highlights, neighborhoods, and practical local guidance.")
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
        return (
            f"All **{len(flights)}** options are **SerpAPI / Google Flights** estimates. "
            "For round-trips, these are low/medium/high outbound tiers enriched with return-leg details."
        )
    if serp == 0:
        return f"All **{len(flights)}** options are **LLM fallback** (SerpAPI flights not configured or no results)."
    return f"**Mixed:** {serp} SerpAPI, {llm} LLM fallback."


def render_flights_picks(plan: FinalPlan) -> None:
    render_story_shell("Flight Chapter", "Provider-backed routes and round-trip payload transparency.")
    st.markdown("### Flight options")
    flights = plan.flights or []
    st.markdown(_flight_plan_summary(flights))
    if not flights:
        st.caption("Set `SERPAPI_API_KEY`, `FLIGHT_DEPARTURE_ID`, and `FLIGHT_ARRIVAL_ID` (or IATA in destination) for live Google Flights bundles.")
        return
    st.caption(
        "Round-trip mode fetches return details for 3 selected outbound tiers (low, medium, high) using departure tokens."
    )
    provider_count = sum(1 for f in flights if "[source:provider:serpapi]" in (f.notes or ""))
    fallback_count = sum(1 for f in flights if "[source:fallback:llm]" in (f.notes or ""))
    render_source_chips(provider_count, fallback_count, "SerpAPI")
    for idx, f in enumerate(flights, start=1):
        src = _flight_row_source(f.notes or "")
        badge_class = "badge" if src == "SerpAPI" else "cost-badge"
        route = html.escape(f.route)
        airline = html.escape(f.airline)
        notes = html.escape(f.notes or "")
        outbound = html.escape((f.outbound_details or "").strip())
        returned = html.escape((f.return_details or "").strip())
        src_e = html.escape(src)
        st.markdown(
            f"""
            <div class="activity-card">
                <b>{idx}. {route}</b>
                <span class="{badge_class}" style="margin-left:0.35rem;">{src_e}</span><br/>
                <span class="activity-detail">{airline} · est. ${f.estimated_cost_usd:,.0f}</span><br/>
                <span class="activity-detail"><b>Outbound:</b> {outbound or "Details unavailable"}</span><br/>
                <span class="activity-detail"><b>Return:</b> {returned or "Details unavailable"}</span><br/>
                <span class="activity-detail">{notes}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(f"Raw flight payloads #{idx} (departure vs return)", expanded=False):
            col_out, col_ret = st.columns(2)
            with col_out:
                st.markdown("**Departure raw**")
                st.json(f.outbound_raw or {"message": "No departure payload captured"})
            with col_ret:
                st.markdown("**Return raw**")
                st.json(f.return_raw or {"message": "No return payload captured"})


def _hotel_row_source(hotel: HotelOption) -> str:
    highlights = " ".join(hotel.highlights or [])
    if "[source:provider:geoapify]" in highlights:
        return "Geoapify"
    return "LLM fallback"


def _hotel_plan_summary(hotels: list[HotelOption]) -> str:
    if not hotels:
        return "No hotel rows returned."
    geo = sum(1 for h in hotels if _hotel_row_source(h) == "Geoapify")
    llm = len(hotels) - geo
    if llm == 0:
        return f"All **{len(hotels)}** options are **Geoapify** accommodation rows."
    if geo == 0:
        return f"All **{len(hotels)}** options are **LLM fallback**."
    return f"**Mixed:** {geo} from Geoapify, {llm} from LLM fallback."


def render_hotels_picks(plan: FinalPlan) -> None:
    render_story_shell("Stay Chapter", "Accommodation options ranked for your travel window.")
    st.markdown("### Hotel options")
    hotels = plan.hotels or []
    st.markdown(_hotel_plan_summary(hotels))
    if not hotels:
        st.caption("Enable `GEOAPIFY_API_KEY` and regenerate to load live hotel rows.")
        return
    geo = sum(1 for h in hotels if _hotel_row_source(h) == "Geoapify")
    llm = len(hotels) - geo
    render_source_chips(geo, llm, "Geoapify")
    for idx, h in enumerate(hotels, start=1):
        src = _hotel_row_source(h)
        badge_class = "badge" if src == "Geoapify" else "cost-badge"
        name = html.escape(h.name)
        area = html.escape(h.area)
        price = html.escape(h.price_range_usd)
        src_e = html.escape(src)
        details = html.escape(" · ".join([x for x in h.highlights if x and "[source:" not in x][:3]))
        st.markdown(
            f"""
            <div class="activity-card">
                <b>{idx}. {name}</b>
                <span class="{badge_class}" style="margin-left:0.35rem;">{src_e}</span><br/>
                <span class="activity-detail">{area} · {price}</span><br/>
                <span class="activity-detail">{details}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_shows_picks(plan: FinalPlan) -> None:
    render_story_shell("Events Chapter", "Timed events inserted around flight constraints.")
    st.markdown("### Shows and events")
    shows = plan.shows or []
    tm = sum(1 for s in shows if "[source:provider:ticketmaster]" in (s.notes or ""))
    if shows:
        if tm == len(shows):
            st.markdown(f"All **{len(shows)}** events are from **Ticketmaster**.")
        elif tm == 0:
            st.markdown(f"All **{len(shows)}** events are non-provider/fallback rows.")
        else:
            st.markdown(f"**Mixed:** {tm} from Ticketmaster, {len(shows) - tm} fallback/other.")
    if not shows:
        st.caption("Set `TICKETMASTER_API_KEY` and regenerate to load live events.")
        return
    for idx, s in enumerate(shows, start=1):
        name = html.escape(s.name)
        venue = html.escape(s.venue)
        when = html.escape(s.local_datetime)
        price = html.escape(s.price_range_usd)
        url = html.escape(s.url or "")
        notes = html.escape(s.notes or "")
        link = f'<a href="{url}" target="_blank">Ticket link</a>' if url else ""
        src = "Ticketmaster" if "[source:provider:ticketmaster]" in (s.notes or "") else "Other"
        src_badge = "badge" if src == "Ticketmaster" else "cost-badge"
        src_e = html.escape(src)
        st.markdown(
            f"""
            <div class="activity-card">
                <b>{idx}. {name}</b>
                <span class="{src_badge}" style="margin-left:0.35rem;">{src_e}</span><br/>
                <span class="activity-detail">{venue} · {when} · {price}</span><br/>
                <span class="activity-detail">{notes}</span><br/>
                <span class="activity-detail">{link}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _places_row_source(place: PlaceOption) -> str:
    if "[source:provider:geoapify]" in (place.notes or ""):
        return "Geoapify"
    return "Unknown"


def render_places_picks(plan: FinalPlan) -> None:
    render_story_shell("Places Chapter", "Must-see landmarks first, then ranked fillers.")
    st.markdown("### Places to visit")
    places = plan.places or []
    if not places:
        st.caption("No places returned for this query. Check destination wording, radius, or Geoapify coverage.")
        return
    must_see = [p for p in places if p.must_see]
    if must_see:
        st.markdown("#### Must See First")
        for idx, p in enumerate(must_see, start=1):
            name = html.escape(p.name)
            category = html.escape(p.category)
            address = html.escape(p.address)
            distance = f"{p.distance_m:.0f}m" if p.distance_m > 0 else "distance N/A"
            st.markdown(
                f"""
                <div class="activity-card">
                    <b>{idx}. {name}</b>
                    <span class="badge" style="margin-left:0.35rem;">Must See</span><br/>
                    <span class="activity-detail">{category} · {distance}</span><br/>
                    <span class="activity-detail">{address}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("#### All places")
    geo = sum(1 for p in places if _places_row_source(p) == "Geoapify")
    render_source_chips(geo, len(places) - geo, "Geoapify")
    if geo == len(places):
        st.markdown(f"All **{len(places)}** places are **Geoapify** attractions POIs.")
    else:
        st.markdown(f"**Mixed:** {geo} from Geoapify, {len(places) - geo} from other sources.")
    for idx, p in enumerate(places, start=1):
        src = _places_row_source(p)
        badge_class = "badge" if src == "Geoapify" else "cost-badge"
        src_e = html.escape(src)
        name = html.escape(p.name)
        category = html.escape(p.category)
        address = html.escape(p.address)
        distance = f"{p.distance_m:.0f}m" if p.distance_m > 0 else "distance N/A"
        link = f'<a href="{html.escape(p.url)}" target="_blank">Website</a>' if (p.url or "").strip() else ""
        notes = html.escape(p.notes or "")
        st.markdown(
            f"""
            <div class="activity-card">
                <b>{idx}. {name}</b>
                <span class="{badge_class}" style="margin-left:0.35rem;">{src_e}</span><br/>
                <span class="activity-detail">{category} · {distance}</span><br/>
                <span class="activity-detail">{address}</span><br/>
                <span class="activity-detail">{notes}</span><br/>
                <span class="activity-detail">{link}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_dining_picks(plan: FinalPlan) -> None:
    """Show full dining list from ``plan.dining`` (Geoapify or LLM)."""
    render_story_shell("Dining Chapter", "Meal ideas matched to your day windows and budget style.")
    st.markdown("### Dining picks")
    dining = plan.dining or []
    st.markdown(_dining_plan_summary(dining))
    if not dining:
        st.caption("Enable `GEOAPIFY_API_KEY` and regenerate to load OSM-backed restaurants.")
        return
    geo = sum(1 for d in dining if "[source:provider:geoapify]" in (d.notes or ""))
    llm = sum(1 for d in dining if "[source:fallback:llm]" in (d.notes or ""))
    render_source_chips(geo, llm, "Geoapify")
    for idx, d in enumerate(dining, start=1):
        src = _dining_row_source(d.notes or "")
        badge_class = "badge" if src == "Geoapify" else "cost-badge"
        name = html.escape(d.name)
        cuisine = html.escape(d.cuisine)
        raw_price = (d.price_level or "").strip()
        price = html.escape(raw_price if raw_price else "$$")
        notes = html.escape(d.notes or "")
        src_e = html.escape(src)
        st.markdown(
            f"""
            <div class="activity-card">
                <b>{idx}. {name}</b>
                <span class="{badge_class}" style="margin-left:0.35rem;">{src_e}</span><br/>
                <span class="activity-detail">{cuisine} · est. price level {price}</span><br/>
                <span class="activity-detail">{notes}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_itinerary_browser(plan: FinalPlan) -> None:
    st.subheader("Day-by-Day Itinerary")
    for day in plan.itinerary.days:
        with st.expander(f"Day {day.day}  |  Total: ${day.day_total_usd:.2f}", expanded=(day.day == 1)):
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


def render_timeline_plan(plan: FinalPlan, selected_flight_idx: int | None = None) -> int | None:
    render_story_shell("Timeline Chapter", "Choose a flight, then review the exact day-by-day execution path.")
    st.subheader("Timeline-First Plan")
    if plan.flight_timelines:
        options = [
            f"{t.flight_label}: {t.route} ({t.airline}, ~${t.estimated_cost_usd:,.0f})"
            for t in plan.flight_timelines
        ]
        selected_idx = selected_flight_idx if selected_flight_idx is not None and 0 <= selected_flight_idx < len(options) else 0
        st.caption("Flight scenario selector")
        cols = st.columns(len(options))
        for idx, option in enumerate(options):
            with cols[idx]:
                active = idx == selected_idx
                label = f"{'● ' if active else ''}{option}"
                if st.button(label, key=f"timeline_flight_{idx}", use_container_width=True):
                    selected_idx = idx
        chosen = plan.flight_timelines[selected_idx]
        entries = sorted(
            chosen.entries,
            key=lambda e: (e.day, e.start_local or f"{e.date} 00:00", e.window),
        )
        st.caption(
            f"Showing per-day itinerary for {chosen.flight_label}: {chosen.route} ({chosen.airline})"
        )
    else:
        entries = sorted(
            plan.timeline,
            key=lambda e: (e.day, e.start_local or f"{e.date} 00:00", e.window),
        )
    if not entries:
        st.caption("No timeline anchors were created; itinerary fallback is shown below.")
        return selected_flight_idx
    grouped: dict[int, list[TimelineEntry]] = {}
    for e in entries:
        grouped.setdefault(e.day, []).append(e)
    for day in sorted(grouped):
        with st.expander(f"Day {day}", expanded=(day == 1)):
            for row in grouped[day]:
                time_span = ""
                if row.start_local and row.end_local:
                    time_span = f"{row.start_local} - {row.end_local}"
                elif row.start_local:
                    time_span = row.start_local
                notes = f" · {row.notes}" if row.notes else ""
                st.markdown(
                    f"- **{row.window.title()}** | {time_span} | {row.title} (`{row.source}`){notes}"
                )
    return selected_idx if plan.flight_timelines else selected_flight_idx


def render_logistics(plan: FinalPlan) -> None:
    render_story_shell("Execution Chapter", "What to book, how to move, and what to pack.")
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


def render_export_summary(plan: FinalPlan, selected_flight_idx: int | None = None) -> None:
    profile = plan.profile
    days = (profile.end_date - profile.start_date).days + 1
    options = flight_budget_options(plan.flights or [])
    if options:
        safe_idx = selected_flight_idx if selected_flight_idx is not None and 0 <= selected_flight_idx < len(options) else 0
        flight_label, flight_cost = options[safe_idx]
        total_cost = estimated_total_spend_usd(plan, selected_flight_cost=flight_cost)
    else:
        flight_label, flight_cost = "No flight selected", estimated_flight_cost_usd(plan.flights or [])
        total_cost = estimated_total_spend_usd(plan)
    st.success(
        f"Ready to export: {profile.destination} | {days} days | "
        f"Estimated spend ${total_cost:,.2f}"
    )
    if flight_cost > 0:
        st.caption(f"Includes flights estimate: ${flight_cost:,.2f} ({flight_label}).")
    st.markdown(
        '<p class="subtle-note">Export your TripForge AI report to share with recruiters, interviewers, clients, or travel partners.</p>',
        unsafe_allow_html=True,
    )

