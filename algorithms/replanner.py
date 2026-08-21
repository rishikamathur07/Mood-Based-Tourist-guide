from heapq import heappop, heappush
from typing import Iterable

from algorithms.knapsack import PlaceCandidate


def pick_replacement(
    candidates: Iterable[PlaceCandidate],
    unavailable_ids: set[str],
    remaining_budget: int,
    remaining_time_mins: int,
) -> PlaceCandidate | None:
    queue: list[tuple[float, str, PlaceCandidate]] = []

    # Priority Queue reasoning:
    # Python's heapq is a min-heap, so we push negative mood scores. That makes
    # the highest mood_match_score come out first while still checking budget
    # and time constraints before accepting a replacement.
    for place in candidates:
        if place.place_id in unavailable_ids:
            continue
        heappush(queue, (-place.mood_match_score, place.name, place))

    while queue:
        _, _, place = heappop(queue)
        if place.avg_cost <= remaining_budget and place.avg_time_spent_mins <= remaining_time_mins:
            return place

    return None
