from collections.abc import Iterable, Mapping

from algorithms.knapsack import PlaceCandidate, choose_places, place_from_mapping
from algorithms.scheduler import ScheduledVisit, schedule_visits
from algorithms.tsp import optimize_route

DEFAULT_DAY_TIME_BUDGET_MINS = 8 * 60


def normalize_places(raw_places: Iterable[Mapping | PlaceCandidate]) -> list[PlaceCandidate]:
    normalized = []
    for place in raw_places:
        if isinstance(place, PlaceCandidate):
            normalized.append(place)
        else:
            normalized.append(place_from_mapping(place))
    return normalized


def generate_itinerary(
    places: Iterable[Mapping | PlaceCandidate],
    city: str,
    mood: str,
    budget: int,
    days: int,
) -> list[ScheduledVisit]:
    """Run the full MVP pipeline: choose, route, then schedule places."""
    candidates = normalize_places(places)
    total_time = days * DEFAULT_DAY_TIME_BUDGET_MINS

    # Pipeline reasoning:
    # 1. Knapsack decides "what to visit" by maximizing mood score under budget/time.
    # 2. TSP heuristics decide "in what order" by reducing travel distance.
    # 3. Greedy scheduling decides "when to visit" while respecting open/close times.
    selected = choose_places(candidates, city=city, mood=mood, budget=budget, total_time_mins=total_time)
    ordered = optimize_route(selected)
    return schedule_visits(ordered, days=days)
