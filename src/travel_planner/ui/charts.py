from __future__ import annotations

import matplotlib.pyplot as plt

from travel_planner.models.schemas import Itinerary


def build_budget_chart(itinerary: Itinerary):
    days = [d.day for d in itinerary.days]
    costs = [d.day_total_usd for d in itinerary.days]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(days, costs, color="#1d4ed8", alpha=0.95, width=0.65)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f8fafc")
    ax.set_title("Daily Budget Estimate (USD)", pad=14, fontsize=13, color="#0f172a")
    ax.set_xlabel("Day")
    ax.set_ylabel("Cost (USD)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.tick_params(colors="#334155")
    ax.grid(axis="y", linestyle="--", alpha=0.2, color="#94a3b8")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, costs):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"${value:.0f}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#1e293b",
            fontweight="bold",
        )
    fig.tight_layout()
    return fig

