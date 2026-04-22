from __future__ import annotations

from datetime import date


def trip_days(start_date: date, end_date: date) -> int:
    days = (end_date - start_date).days + 1
    return max(days, 1)

