"""
Traveling Salesperson Problem (TSP) Optimization: Nearest Neighbor + 2-opt.

College Viva Summary:
---------------------
1. Problem:
   Given a set of tourist attractions chosen by the 0/1 Knapsack stage, find the
   visitation order that MINIMIZES total transit distance (and time), reducing
   fatigue and unnecessary backtracking.
   TSP is an NP-hard problem; finding the exact global optimum via brute force O(N!)
   is intractable even for moderate N.

2. Heuristic Solution (2-stage hybrid):
   Stage A: Nearest Neighbor (Constructive Heuristic)
     - Starts from the tourist's designated origin (e.g. hotel, landmark, or city center).
     - Greedily selects the closest unvisited attraction based on Haversine distance.
     - Fast O(N^2) construction producing a sensible initial tour.

   Stage B: 2-opt (Local Search Improvement Heuristic)
     - Iteratively tests pairs of route edges (A-B and C-D). If reversing the sub-tour
       between them removes an edge-crossing and yields a shorter total distance, the
       reversal is committed.
     - Continues until no 2-edge exchange yields further reduction (local optimum reached).
     - Guarantees route crossings are eliminated.

3. Distance Calculation:
   - Haversine formula calculates great-circle distance between two latitude/longitude
     coordinates on a spherical Earth (mean radius R = 6371.0 km).
"""

from math import asin, cos, radians, sin, sqrt
from typing import Sequence

from algorithms.knapsack import PlaceCandidate


def haversine_km(a: PlaceCandidate, b: PlaceCandidate) -> float:
    """
    Great-circle distance between two geographic coordinates in kilometers.

    Formula:
    a = sin^2(dlat/2) + cos(lat1) * cos(lat2) * sin^2(dlon/2)
    c = 2 * R * asin(sqrt(a))
    """
    radius_km = 6371.0
    lat1 = radians(a.latitude)
    lon1 = radians(a.longitude)
    lat2 = radians(b.latitude)
    lon2 = radians(b.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = sin(dlat / 2.0) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2.0) ** 2
    return 2.0 * radius_km * asin(sqrt(value))


def route_distance_km(route: Sequence[PlaceCandidate]) -> float:
    """Total travel distance across an ordered sequence of places."""
    return sum(haversine_km(route[index], route[index + 1]) for index in range(len(route) - 1))


def nearest_neighbor_order(
    places: Sequence[PlaceCandidate],
    start_coordinate: tuple[float, float] | None = None,
) -> list[PlaceCandidate]:
    """
    Greedy constructive heuristic for TSP.

    If `start_coordinate` is provided (e.g. tourist hotel or landmark),
    seeds the tour with the attraction geographically closest to that origin.
    """
    if not places:
        return []

    unvisited = list(places)
    if start_coordinate is None:
        route = [unvisited.pop(0)]
    else:
        start_lat, start_lon = start_coordinate
        # Choose closest attraction to start coordinate
        first_place = min(
            unvisited,
            key=lambda place: (place.latitude - start_lat) ** 2 + (place.longitude - start_lon) ** 2,
        )
        route = [first_place]
        unvisited.remove(first_place)

    while unvisited:
        current = route[-1]
        closest = min(unvisited, key=lambda place: haversine_km(current, place))
        route.append(closest)
        unvisited.remove(closest)

    return route


def two_opt(route: Sequence[PlaceCandidate]) -> list[PlaceCandidate]:
    """
    2-opt local search optimization.

    Replaces crossed route segments with non-crossing shorter connections.
    Reverses the segment between indices i and j when candidate distance < best distance.
    """
    best = list(route)
    improved = True

    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                # Reverse sub-sequence between i and j
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                if route_distance_km(candidate) < route_distance_km(best):
                    best = candidate
                    improved = True
        route = best

    return best


def optimize_route(
    places: Sequence[PlaceCandidate],
    start_coordinate: tuple[float, float] | None = None,
) -> list[PlaceCandidate]:
    """
    Combines Nearest Neighbor construction with 2-opt post-optimization.
    """
    return two_opt(nearest_neighbor_order(places, start_coordinate=start_coordinate))
