"""
Greedy Interval Scheduling Module for Itinerary Time Windows.

College Viva Summary:
---------------------
1. Problem:
   Given an ordered sequence of tourist places to visit over `days` days, schedule each
   visit into a realistic daily time window (default 9:00 AM to 8:00 PM). Each place
   has specific operational hours (opening/closing minutes from midnight) and a required
   visit duration (`avg_time_spent_mins`). Visits must also include realistic transit
   buffers between stops.

2. Algorithm & Greedy Strategy:
   - Earliest-Finish Time / Earliest-Feasible Start Scheduling.
   - For each place, compute `start = max(current_time, place.opening_minutes, day_start)`.
   - Compute `end = start + avg_time_spent_mins`.
   - If `end > min(place.closing_minutes, day_end)`, the visit cannot complete today.
     The algorithm advances to `current_day + 1` at `day_start`.
   - If feasible within the remaining days, the visit is locked in, and `current_time`
     advances to `end + travel_buffer_minutes`.
   - This greedy approach maximizes remaining day capacity for subsequent attractions.

3. Complexity:
   - Time Complexity: O(N) where N is the number of ordered places.
   - Space Complexity: O(N) to store scheduled visits.
"""

from dataclasses import dataclass
from typing import Sequence

from algorithms.knapsack import PlaceCandidate

DAY_START_MINUTES = 9 * 60       # 9:00 AM (540 minutes from midnight)
DAY_END_MINUTES = 20 * 60        # 8:00 PM (1200 minutes from midnight)
TRAVEL_BUFFER_MINUTES = 30       # 30-minute standard transit buffer between stops


@dataclass(frozen=True)
class ScheduledVisit:
    place: PlaceCandidate
    day: int
    start_minutes: int
    end_minutes: int


def format_minutes(minutes: int) -> str:
    """Format minutes-from-midnight as 12-hour clock, e.g. 9:00 AM or 2:30 PM."""
    minutes = max(0, int(minutes))
    hours_24 = minutes // 60
    mins = minutes % 60
    period = "AM" if hours_24 < 12 else "PM"
    hours_12 = hours_24 % 12 or 12
    if mins:
        return f"{hours_12}:{mins:02d} {period}"
    return f"{hours_12} {period}"


def format_duration(minutes: int) -> str:
    """Format duration in minutes as human-readable string (e.g. 1 hr 30 min)."""
    minutes = max(0, int(minutes))
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours} hr {mins} min"
    if hours:
        return f"{hours} hr"
    return f"{mins} min"


def schedule_visits(
    ordered_places: Sequence[PlaceCandidate],
    days: int,
    day_start: int = DAY_START_MINUTES,
    day_end: int = DAY_END_MINUTES,
    travel_buffer: int = TRAVEL_BUFFER_MINUTES,
) -> list[ScheduledVisit]:
    """
    Greedy interval scheduling that assigns each place to a day and time slot.
    """
    scheduled: list[ScheduledVisit] = []
    current_day = 1
    current_time = day_start

    for place in ordered_places:
        if current_day > days:
            break

        # Calculate earliest valid start time
        start = max(current_time, place.opening_minutes, day_start)
        end = start + place.avg_time_spent_mins

        # If it overflows venue closing time or daily end window, shift to next day
        if end > min(place.closing_minutes, day_end):
            current_day += 1
            if current_day > days:
                break
            start = max(day_start, place.opening_minutes)
            end = start + place.avg_time_spent_mins

        if end <= min(place.closing_minutes, day_end):
            scheduled.append(
                ScheduledVisit(
                    place=place,
                    day=current_day,
                    start_minutes=start,
                    end_minutes=end,
                )
            )
            current_time = end + travel_buffer

    return scheduled
