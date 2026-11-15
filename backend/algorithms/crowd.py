"""Crowd-aware ordering helpers for itinerary re-planning."""

from heapq import heappop, heappush
from typing import Sequence

from algorithms.knapsack import PlaceCandidate


CROWD_PRIORITY = {"High": 0, "Medium": 1, "Low": 2}


def crowd_aware_order(places: Sequence[PlaceCandidate], crowd_levels: dict[str, str]) -> list[PlaceCandidate]:
    """Put busier stops earlier with a priority queue.

    High-crowd places receive the smallest priority and are popped first. This
    greedy choice gives them morning time slots before queues usually build,
    while the original route index breaks ties predictably.
    """
    queue: list[tuple[int, int, PlaceCandidate]] = []
    for index, place in enumerate(places):
        priority = CROWD_PRIORITY.get(crowd_levels.get(place.place_id, "Medium"), 1)
        heappush(queue, (priority, index, place))
    return [heappop(queue)[2] for _ in range(len(queue))]
