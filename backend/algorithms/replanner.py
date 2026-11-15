"""
Priority Queue-based Replanner Module for Live Itinerary Re-planning.

College Viva Summary:
---------------------
1. Problem:
   During live travel, a tourist may discover a venue is unexpectedly closed,
   unavailable, or overly crowded. The system must swap out that stop and recommend
   the best immediate replacement without recomputing the entire multi-day itinerary.

2. Data Structure & Algorithm:
   - Priority Queue (Min-Heap via Python's `heapq` module).
   - Priority Key: Since `heapq` implements a min-heap, we invert the mood-match
     score (using `-mood_match_score`), optionally adjusted by crowd penalty.
     This guarantees O(log N) extraction of the candidate with the highest
     preference value.
   - Constraint Verification: Before returning a candidate, we verify that its
     cost fits `remaining_budget` and its duration fits `remaining_time_mins`.

3. Complexity:
   - Building Heap: O(N log N) or O(N) using heapify.
   - Extracting Best Valid Candidate: O(K log N) where K is the number of popped
     candidates before the feasibility predicate holds (usually K=1).
"""

from heapq import heappop, heappush
from typing import Iterable

from algorithms.knapsack import PlaceCandidate


def pick_replacement(
    candidates: Iterable[PlaceCandidate],
    unavailable_ids: set[str],
    remaining_budget: int,
    remaining_time_mins: int,
    prefer_lower_crowd: bool = False,
    crowd_levels: dict[str, str] | None = None,
) -> PlaceCandidate | None:
    """
    Select the highest mood-match replacement candidate using a Priority Queue.

    Parameters:
    - candidates: Places available in the city/mood tag not currently on the itinerary.
    - unavailable_ids: Set of place_ids marked closed/crowded or already visited.
    - remaining_budget: Maximum available monetary budget for this replacement stop.
    - remaining_time_mins: Maximum visit duration that fits the day schedule.
    - prefer_lower_crowd: If True (e.g. user selected 'mark crowded'), penalizes High crowd stops.
    - crowd_levels: Optional mapping of place_id -> crowd level string ('Low', 'Medium', 'High').

    Returns:
    - Best PlaceCandidate matching constraints, or None if no candidate is feasible.
    """
    queue: list[tuple[float, int, str, PlaceCandidate]] = []
    crowd_map = crowd_levels or {}

    # Tie-breaker counter to avoid comparing PlaceCandidate objects if scores and names collide
    counter = 0

    for place in candidates:
        if place.place_id in unavailable_ids:
            continue

        effective_score = place.mood_match_score

        # When the user is replacing a crowded venue, prioritize calmer venues
        if prefer_lower_crowd:
            crowd = crowd_map.get(place.place_id, "Medium")
            if crowd == "Low":
                effective_score += 1.0
            elif crowd == "High":
                effective_score -= 1.5

        # Negate score so highest positive score becomes smallest float (min-heap top)
        priority_key = -effective_score
        counter += 1
        heappush(queue, (priority_key, counter, place.name, place))

    # Sequentially test candidates from highest to lowest score
    while queue:
        _, _, _, place = heappop(queue)
        if place.avg_cost <= remaining_budget and place.avg_time_spent_mins <= remaining_time_mins:
            return place

    return None
