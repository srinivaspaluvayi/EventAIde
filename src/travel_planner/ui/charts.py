from __future__ import annotations

import matplotlib.pyplot as plt

from travel_planner.models.schemas import Itinerary


def build_budget_chart(itinerary: Itinerary):
    days = [d.day for d in itinerary.days]
    costs = [d.day_total_usd for d in itinerary.days]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(days, costs, color="#2563eb", alpha=0.9)
    ax.set_title("Daily Budget Estimate (USD)", pad=14, fontsize=13)
    ax.set_xlabel("Day")
    ax.set_ylabel("Cost (USD)")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, costs):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"${value:.0f}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#334155",
        )
    fig.tight_layout()
    return fig

