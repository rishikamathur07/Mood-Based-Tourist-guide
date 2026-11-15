"""
0/1 Knapsack Module for Tourist Attraction Selection.

College Viva Summary:
---------------------
1. Problem:
   Given a set of candidate tourist attractions in a chosen city matching the user's mood,
   each place having an entry cost, average time spent (minutes), and a mood-match score.
   Goal: Select a subset of places to visit that MAXIMIZES the total mood-match score
   WITHOUT exceeding the user's allocated monetary budget AND available daily time window.

2. Formulation:
   - This is a Multi-dimensional (2-capacity) 0/1 Knapsack Problem.
   - Capacities:
     1) Monetary Budget (B)
     2) Available Tour Time in minutes (T)
   - Value: `mood_match_score`
   - "0/1" Constraint: Each place can either be visited once (1) or not at all (0).

3. Algorithm:
   - Dynamic Programming (DP).
   - State Definition: `dp[(b, t)]` stores the maximum mood-match score obtainable
     using a subset of examined attractions using at most `b` budget and `t` time.
   - Backward Transition / Space Optimization: We maintain a state map and update
     it in a single-layer table to conserve memory while guaranteeing no place is
     counted multiple times in the same iteration.

4. Time & Space Complexity:
   - Time Complexity: O(N * |reachable states|) <= O(N * B * T).
   - Space Complexity: O(|reachable states|).
"""

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class PlaceCandidate:
    place_id: str
    name: str
    city: str
    mood_tag: str
    latitude: float
    longitude: float
    avg_cost: int
    avg_time_spent_mins: int
    opening_minutes: int
    closing_minutes: int
    mood_match_score: float
    category: str = "Other"


def place_from_mapping(row: Mapping) -> PlaceCandidate:
    """Helper to convert a dict/row mapping into an immutable PlaceCandidate."""
    return PlaceCandidate(
        place_id=str(row["place_id"]),
        name=str(row["name"]),
        city=str(row["city"]),
        mood_tag=str(row["mood_tag"]),
        latitude=float(row["latitude"]),
        longitude=float(row["longitude"]),
        avg_cost=int(float(row["avg_cost"])),
        avg_time_spent_mins=int(float(row["avg_time_spent_mins"])),
        opening_minutes=int(float(row["opening_minutes"])),
        closing_minutes=int(float(row["closing_minutes"])),
        mood_match_score=float(row["mood_match_score"]),
        category=str(row.get("category") or "Other"),
    )


def choose_places(
    places: Iterable[PlaceCandidate],
    city: str,
    mood: str,
    budget: int,
    total_time_mins: int,
) -> list[PlaceCandidate]:
    """
    Select places using 0/1 Knapsack Dynamic Programming under dual capacities: budget and time.

    College Viva note:
    Filtering out places exceeding individual limits prunes infeasible states upfront.
    Hotels are excluded because they represent lodging accommodations, not visitable stops.
    """
    filtered = [
        place
        for place in places
        if place.city.lower() == city.lower()
        and place.mood_tag.lower() == mood.lower()
        and place.category.lower() != "hotel"
        and place.avg_cost <= budget
        and place.avg_time_spent_mins <= total_time_mins
    ]

    # dp map: (used_budget, used_time) -> maximum mood_match_score achieved
    dp: dict[tuple[int, int], float] = {(0, 0): 0.0}
    # chosen map: (used_budget, used_time) -> list of PlaceCandidates in that solution
    chosen: dict[tuple[int, int], list[PlaceCandidate]] = {(0, 0): []}

    for place in filtered:
        next_dp = dict(dp)
        next_chosen = dict(chosen)
        for (used_budget, used_time), score in dp.items():
            new_budget = used_budget + place.avg_cost
            new_time = used_time + place.avg_time_spent_mins
            if new_budget > budget or new_time > total_time_mins:
                continue

            new_state = (new_budget, new_time)
            new_score = score + place.mood_match_score
            if new_score > next_dp.get(new_state, -1.0):
                next_dp[new_state] = new_score
                next_chosen[new_state] = chosen[(used_budget, used_time)] + [place]

        dp = next_dp
        chosen = next_chosen

    best_state = max(dp, key=lambda state: dp[state])
    return chosen[best_state]
