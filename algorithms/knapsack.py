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
    """Pick places with 0/1 knapsack using budget and time as two capacities."""
    filtered = [
        place
        for place in places
        if place.city.lower() == city.lower()
        and place.mood_tag.lower() == mood.lower()
        and place.avg_cost <= budget
        and place.avg_time_spent_mins <= total_time_mins
    ]

    # State definition:
    # dp[i][b][t] would mean "best score using first i places within b cost and t minutes".
    # To save memory, we keep only one layer: dp[(b, t)] stores the best score for capacities
    # b and t after processing the places seen so far. Iterating capacities backwards is what
    # makes this 0/1: each place can be used at most once, because the current place cannot
    # immediately feed into another state in the same iteration.
    dp: dict[tuple[int, int], float] = {(0, 0): 0.0}
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
            if new_score > next_dp.get(new_state, -1):
                next_dp[new_state] = new_score
                next_chosen[new_state] = chosen[(used_budget, used_time)] + [place]

        dp = next_dp
        chosen = next_chosen

    best_state = max(dp, key=lambda state: dp[state])
    return chosen[best_state]
