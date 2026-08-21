from math import asin, cos, radians, sin, sqrt
from typing import Sequence

from algorithms.knapsack import PlaceCandidate


def haversine_km(a: PlaceCandidate, b: PlaceCandidate) -> float:
    radius_km = 6371.0
    lat1 = radians(a.latitude)
    lon1 = radians(a.longitude)
    lat2 = radians(b.latitude)
    lon2 = radians(b.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * radius_km * asin(sqrt(value))


def route_distance_km(route: Sequence[PlaceCandidate]) -> float:
    return sum(haversine_km(route[index], route[index + 1]) for index in range(len(route) - 1))


def nearest_neighbor_order(places: Sequence[PlaceCandidate]) -> list[PlaceCandidate]:
    if not places:
        return []

    # Nearest Neighbor is a greedy TSP heuristic: start somewhere, repeatedly
    # visit the closest unvisited node. It is fast and easy to explain, though
    # not guaranteed optimal, which is why 2-opt improves it afterward.
    unvisited = list(places)
    route = [unvisited.pop(0)]

    while unvisited:
        current = route[-1]
        closest = min(unvisited, key=lambda place: haversine_km(current, place))
        route.append(closest)
        unvisited.remove(closest)

    return route


def two_opt(route: Sequence[PlaceCandidate]) -> list[PlaceCandidate]:
    best = list(route)
    improved = True

    # 2-opt improves a route by reversing a middle segment when two crossing
    # edges can be replaced by two shorter non-crossing edges. We keep applying
    # local improvements until no pair reversal shortens the route.
    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                if route_distance_km(candidate) < route_distance_km(best):
                    best = candidate
                    improved = True
        route = best

    return best


def optimize_route(places: Sequence[PlaceCandidate]) -> list[PlaceCandidate]:
    return two_opt(nearest_neighbor_order(places))
