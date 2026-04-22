from datetime import date

from travel_planner.models.schemas import Activity, DayPlan, Itinerary, TravelProfile


def test_travel_profile_and_itinerary_schema():
    profile = TravelProfile(
        destination="Tokyo",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        budget_usd=1800,
        travel_style="balanced",
        interests=["food", "culture"],
        group_size=1,
    )
    act = Activity(slot="morning", title="Walk", details="City walk", estimated_cost_usd=20)
    day = DayPlan(day=1, morning=act, afternoon=act, evening=act, day_total_usd=60)
    itinerary = Itinerary(trip_title="Tokyo Plan", days=[day], estimated_total_usd=60)
    assert profile.destination == "Tokyo"
    assert itinerary.days[0].day == 1

