from __future__ import annotations

import html as html_lib
from pathlib import Path

from travel_planner.models.schemas import DestinationInfo, Itinerary, Logistics, TravelProfile


def render_html(
    profile: TravelProfile,
    destination_info: DestinationInfo,
    itinerary: Itinerary,
    logistics: Logistics,
    output_path: str = "output/travel_plan.html",
) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    duration_days = (profile.end_date - profile.start_date).days + 1

    def _escape(value: str) -> str:
        return html_lib.escape(value, quote=True)

    def _list_items(values: list[str]) -> str:
        return "".join(f"<li>{_escape(item)}</li>" for item in values) if values else "<li>Not specified</li>"

    days_html = []
    for day in itinerary.days:
        days_html.append(
            f"""
            <section class="day-card">
              <div class="day-header">
                <h3>Day {day.day}</h3>
                <span class="pill">Total ${day.day_total_usd:.2f}</span>
              </div>
              <div class="timeline">
                <div class="timeline-item">
                  <h4>Morning · {_escape(day.morning.title)}</h4>
                  <p>{_escape(day.morning.details)}</p>
                  <span class="cost">${day.morning.estimated_cost_usd:.2f}</span>
                </div>
                <div class="timeline-item">
                  <h4>Afternoon · {_escape(day.afternoon.title)}</h4>
                  <p>{_escape(day.afternoon.details)}</p>
                  <span class="cost">${day.afternoon.estimated_cost_usd:.2f}</span>
                </div>
                <div class="timeline-item">
                  <h4>Evening · {_escape(day.evening.title)}</h4>
                  <p>{_escape(day.evening.details)}</p>
                  <span class="cost">${day.evening.estimated_cost_usd:.2f}</span>
                </div>
              </div>
            </section>
            """
        )

    budget_rows = "".join(
        f"<tr><td>Day {day.day}</td><td>${day.day_total_usd:.2f}</td></tr>"
        for day in itinerary.days
    )

    rendered_html = f"""
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{_escape(itinerary.trip_title)}</title>
        <style>
          :root {{
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #0f172a;
            --muted: #475569;
            --brand: #1d4ed8;
            --line: #e2e8f0;
            --pill: #dbeafe;
          }}
          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
            color: var(--text);
            background: var(--bg);
          }}
          .wrap {{
            max-width: 980px;
            margin: 0 auto;
            padding: 24px;
          }}
          .hero {{
            background: radial-gradient(circle at top left, #1d4ed8 0%, #0f172a 55%);
            color: white;
            border-radius: 16px;
            padding: 22px;
            margin-bottom: 16px;
            box-shadow: 0 14px 32px rgba(15, 23, 42, 0.22);
          }}
          .hero h1 {{ margin: 0 0 8px 0; font-size: 1.8rem; }}
          .flow-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
          }}
          .flow-pill {{
            font-size: 0.76rem;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.2);
          }}
          .grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 16px;
          }}
          .kpi {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px;
          }}
          .kpi .label {{ font-size: 0.8rem; color: var(--muted); }}
          .kpi .value {{ font-size: 1.1rem; font-weight: 700; margin-top: 4px; }}
          .section {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 14px;
          }}
          h2 {{ margin: 0 0 12px 0; font-size: 1.25rem; }}
          .columns {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
          }}
          ul {{ margin: 6px 0 0 16px; padding: 0; }}
          li {{ margin-bottom: 6px; color: var(--muted); }}
          .pill {{
            background: var(--pill);
            color: #1e3a8a;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.78rem;
            font-weight: 700;
          }}
          .day-card {{
            background: #f8fafc;
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px;
            margin-bottom: 10px;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
          }}
          .day-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
          }}
          .day-header h3 {{ margin: 0; }}
          .timeline-item {{
            border-left: 3px solid #bfdbfe;
            padding: 6px 0 8px 10px;
            margin-bottom: 8px;
          }}
          .timeline-item h4 {{ margin: 0 0 4px 0; font-size: 0.96rem; }}
          .timeline-item p {{ margin: 0 0 4px 0; color: var(--muted); font-size: 0.92rem; }}
          .cost {{ font-weight: 700; color: #1d4ed8; font-size: 0.9rem; }}
          table {{
            border-collapse: collapse;
            width: 100%;
            margin-top: 8px;
            border-radius: 8px;
            overflow: hidden;
          }}
          th, td {{
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid var(--line);
          }}
          th {{ background: #eff6ff; }}
          .right {{ text-align: right; }}
          .foot-note {{
            margin-top: 10px;
            font-size: 0.82rem;
            color: var(--muted);
          }}
          @media (max-width: 860px) {{
            .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .columns {{ grid-template-columns: 1fr; }}
          }}
          @media print {{
            body {{ background: white; }}
            .wrap {{ max-width: 100%; padding: 0; }}
            .section, .day-card, .kpi {{ break-inside: avoid; }}
          }}
        </style>
      </head>
      <body>
        <main class="wrap">
          <section class="hero">
            <h1>{_escape(itinerary.trip_title)}</h1>
            <p>TripForge AI report generated from traveler preferences, destination insights, and budget constraints.</p>
            <div class="flow-row">
              <span class="flow-pill">Preferences</span>
              <span class="flow-pill">Research</span>
              <span class="flow-pill">Itinerary</span>
              <span class="flow-pill">Logistics</span>
              <span class="flow-pill">Export</span>
            </div>
          </section>
          <section class="grid">
            <div class="kpi"><div class="label">Destination</div><div class="value">{_escape(profile.destination)}</div></div>
            <div class="kpi"><div class="label">Trip Dates</div><div class="value">{profile.start_date} to {profile.end_date}</div></div>
            <div class="kpi"><div class="label">Trip Length</div><div class="value">{duration_days} days</div></div>
            <div class="kpi"><div class="label">Budget</div><div class="value">${profile.budget_usd:.2f}</div></div>
          </section>

          <section class="section">
            <h2>Traveler Profile</h2>
            <p><b>Travel Style:</b> {_escape(profile.travel_style)}</p>
            <p><b>Interests:</b> {_escape(", ".join(profile.interests))}</p>
          </section>

          <section class="section columns">
            <div>
              <h2>Destination Insights</h2>
              <p><b>Highlights</b></p>
              <ul>{_list_items(destination_info.highlights)}</ul>
              <p><b>Best Areas To Stay</b></p>
              <ul>{_list_items(destination_info.best_areas_to_stay)}</ul>
            </div>
            <div>
              <h2>Travel Essentials</h2>
              <p><b>Local Tips</b></p>
              <ul>{_list_items(destination_info.local_tips)}</ul>
              <p><b>Visa:</b> {_escape(destination_info.visa_requirements)}</p>
              <p><b>Weather:</b> {_escape(destination_info.weather_summary)}</p>
            </div>
          </section>

          <section class="section">
            <h2>Day-by-Day Itinerary</h2>
            {''.join(days_html)}
          </section>

          <section class="section columns">
            <div><h2>Accommodation</h2><ul>{_list_items(logistics.accommodation_options)}</ul></div>
            <div><h2>Transport</h2><ul>{_list_items(logistics.local_transport)}</ul></div>
          </section>
          <section class="section"><h2>Packing Tips</h2><ul>{_list_items(logistics.packing_tips)}</ul></section>

          <section class="section">
            <h2>Budget Summary</h2>
            <table>
              <thead>
                <tr><th>Day</th><th class="right">Estimated Cost (USD)</th></tr>
              </thead>
              <tbody>
                {budget_rows}
                <tr><th>Total</th><th class="right">${itinerary.estimated_total_usd:.2f}</th></tr>
              </tbody>
            </table>
            <p class="foot-note">All costs are estimates and may vary by season, provider availability, and booking window.</p>
          </section>
        </main>
      </body>
    </html>
    """
    path.write_text(rendered_html, encoding="utf-8")
    return str(path)

