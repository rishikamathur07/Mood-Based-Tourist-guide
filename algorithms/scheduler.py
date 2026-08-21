from dataclasses import dataclass
from typing import Sequence

from algorithms.knapsack import PlaceCandidate

DAY_START_MINUTES = 9 * 60
DAY_END_MINUTES = 20 * 60
TRAVEL_BUFFER_MINUTES = 30


@dataclass(frozen=True)
class ScheduledVisit:
    place: PlaceCandidate
    day: int
    start_minutes: int
    end_minutes: int


def format_minutes(minutes: int) -> str:
    """Format minutes-from-midnight as 12-hour clock, e.g. 9:00 AM."""
    minutes = max(0, int(minutes))
    hours_24 = minutes // 60
    mins = minutes % 60
    period = "AM" if hours_24 < 12 else "PM"
    hours_12 = hours_24 % 12 or 12
    if mins:
        return f"{hours_12}:{mins:02d} {period}"
    return f"{hours_12} {period}"


def format_duration(minutes: int) -> str:
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
    scheduled: list[ScheduledVisit] = []
    current_day = 1
    current_time = day_start

    for place in ordered_places:
        if current_day > days:
            break

        # Greedy interval scheduling idea:
        # place each visit at the earliest valid time that respects both the
        # tourist's day window and the place's opening interval. Earliest-finish
        # placement leaves the maximum remaining room for later visits.
        start = max(current_time, place.opening_minutes, day_start)
        end = start + place.avg_time_spent_mins

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
