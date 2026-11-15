"""
Graph Algorithms Module: Dijkstra, A*, Floyd-Warshall, and Prim's MST.

College Viva Summary:
---------------------
1. Graph Representation:
   - Adjacency list: `Graph = dict[str, list[Edge]]`.
   - Each selected tourist place is a vertex (node).
   - Edges represent travel between places.
   - Edge Weights: Driving travel time in minutes. By default, derived from
     Haversine distance (spherical trigonometry assuming city driving speed 28 km/h).
     When `google_maps_api_key` is configured, weights are queried from the
     Google Maps Distance Matrix API (real-world road distance and live traffic duration).

2. Dijkstra's Algorithm:
   - Single-source shortest path on graphs with non-negative edge weights.
   - Uses a Min-Heap priority queue (`heapq`) to greedily expand the frontier vertex
     with minimum cumulative travel time.
   - Time Complexity: O((V + E) log V).

3. A* Search Algorithm:
   - Informed search extending Dijkstra with an admissible heuristic `h(n)`.
   - Evaluation function: `f(n) = g(n) + h(n)`
     - `g(n)`: exact travel time from start to vertex `n`.
     - `h(n)`: straight-line travel time from `n` to goal (estimated via Haversine distance).
   - Admissibility: Because straight-line distance is always <= road distance, `h(n)`
     never overestimates the true remaining travel time. This guarantees optimality
     while expanding fewer search states than Dijkstra.

4. Prim's Minimum Spanning Tree (MST):
   - Finds the subset of edges connecting all tourist places with minimal total travel time.
   - Used to generate an optimal interconnected network/backbone of attractions.
   - Time Complexity: O(E log V).

5. Floyd-Warshall Algorithm:
   - Dynamic Programming all-pairs shortest path.
   - State transition: `dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])`
     for each intermediate vertex `k`.
   - Computes travel matrix between all stops in O(V^3).
"""

from dataclasses import dataclass
from heapq import heappop, heappush
from math import inf
import os
from typing import Callable, Iterable
import urllib.parse
import urllib.request
import json

from algorithms.knapsack import PlaceCandidate
from algorithms.tsp import haversine_km


@dataclass(frozen=True)
class Edge:
    target_id: str
    distance_km: float
    travel_minutes: float


Graph = dict[str, list[Edge]]


def estimate_travel_minutes(distance_km: float, average_speed_kmph: float = 28.0) -> float:
    """Estimated city transit time in minutes based on distance."""
    return (distance_km / average_speed_kmph) * 60.0


def fetch_google_distance_matrix(
    places: list[PlaceCandidate],
    api_key: str,
    timeout_seconds: float = 3.0,
) -> dict[tuple[str, str], tuple[float, float]] | None:
    """
    Fetch real road distance (km) and driving time (minutes) from Google Distance Matrix API.

    Returns:
    - Mapping (source_id, target_id) -> (distance_km, travel_minutes), or None if call fails.
    """
    if not api_key or not places:
        return None

    # Limit to reasonable matrix size (at most 10 places = 100 elements)
    subset = places[:10]
    coords = [f"{p.latitude},{p.longitude}" for p in subset]
    origins_param = "|".join(coords)
    destinations_param = "|".join(coords)

    query = urllib.parse.urlencode(
        {
            "origins": origins_param,
            "destinations": destinations_param,
            "mode": "driving",
            "key": api_key,
        }
    )
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?{query}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MoodTouristGuide/2.0"})
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if payload.get("status") != "OK":
            return None

        matrix: dict[tuple[str, str], tuple[float, float]] = {}
        rows = payload.get("rows", [])
        for i, row in enumerate(rows):
            src_id = subset[i].place_id
            elements = row.get("elements", [])
            for j, element in enumerate(elements):
                tgt_id = subset[j].place_id
                if src_id == tgt_id:
                    continue
                if element.get("status") == "OK":
                    dist_km = element.get("distance", {}).get("value", 0) / 1000.0
                    dur_min = element.get("duration", {}).get("value", 0) / 60.0
                    matrix[(src_id, tgt_id)] = (dist_km, dur_min)

        return matrix
    except Exception:
        # Graceful fallback: sandbox or network restrictions should never crash the system
        return None


def build_place_graph(
    places: Iterable[PlaceCandidate],
    api_key: str | None = None,
) -> Graph:
    """
    Construct a complete weighted directed graph of places.

    When `api_key` (Google Maps API Key) is present, attempts to use Google Distance Matrix
    for edge weights. If absent, offline, or restricted, seamlessly uses Haversine geodesic
    distances and average transit speed.
    """
    nodes = list(places)
    graph: Graph = {place.place_id: [] for place in nodes}

    # Optional Google Distance Matrix integration
    resolved_api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    matrix_weights = None
    if resolved_api_key and "paste-your-real" not in resolved_api_key:
        matrix_weights = fetch_google_distance_matrix(nodes, resolved_api_key)

    for source in nodes:
        for target in nodes:
            if source.place_id == target.place_id:
                continue

            if matrix_weights and (source.place_id, target.place_id) in matrix_weights:
                distance_km, travel_min = matrix_weights[(source.place_id, target.place_id)]
            else:
                distance_km = haversine_km(source, target)
                travel_min = estimate_travel_minutes(distance_km)

            graph[source.place_id].append(
                Edge(
                    target_id=target.place_id,
                    distance_km=distance_km,
                    travel_minutes=travel_min,
                )
            )

    return graph


def dijkstra(graph: Graph, start_id: str, end_id: str) -> tuple[float, list[str]]:
    """
    Dijkstra's Single-Source Shortest Path using Min-Heap.

    College Viva note:
    Guaranteed optimal because all travel_minutes >= 0. Once destination `end_id`
    is popped from the priority queue, no shorter path can exist.
    """
    distances = {node_id: inf for node_id in graph}
    previous: dict[str, str | None] = {node_id: None for node_id in graph}
    distances[start_id] = 0.0
    queue: list[tuple[float, str]] = [(0.0, start_id)]

    while queue:
        current_distance, current_id = heappop(queue)
        if current_distance > distances[current_id]:
            continue
        if current_id == end_id:
            break

        for edge in graph.get(current_id, []):
            new_distance = current_distance + edge.travel_minutes
            if new_distance < distances[edge.target_id]:
                distances[edge.target_id] = new_distance
                previous[edge.target_id] = current_id
                heappush(queue, (new_distance, edge.target_id))

    return distances[end_id], reconstruct_path(previous, end_id)


def astar(
    graph: Graph,
    start_id: str,
    end_id: str,
    heuristic: Callable[[str, str], float],
) -> tuple[float, list[str]]:
    """
    A* Shortest Path with an admissible heuristic `h(n)`.

    College Viva note:
    f(n) = g(n) + h(n). Nodes topologically closer to the goal are explored first,
    dramatically reducing the search space compared to Dijkstra while preserving optimality.
    """
    g_score = {node_id: inf for node_id in graph}
    previous: dict[str, str | None] = {node_id: None for node_id in graph}
    g_score[start_id] = 0.0

    # (f_score, current_id)
    queue: list[tuple[float, str]] = [(heuristic(start_id, end_id), start_id)]

    while queue:
        _, current_id = heappop(queue)
        if current_id == end_id:
            break

        for edge in graph.get(current_id, []):
            tentative = g_score[current_id] + edge.travel_minutes
            if tentative < g_score[edge.target_id]:
                previous[edge.target_id] = current_id
                g_score[edge.target_id] = tentative
                f_score = tentative + heuristic(edge.target_id, end_id)
                heappush(queue, (f_score, edge.target_id))

    return g_score[end_id], reconstruct_path(previous, end_id)


def prim_mst(graph: Graph, start_id: str) -> tuple[float, list[tuple[str, str, float]]]:
    """
    Prim's Algorithm for Minimum Spanning Tree (MST).

    Finds the minimum total travel-time tree connecting every selected attraction.
    """
    visited = {start_id}
    queue: list[tuple[float, str, str]] = []
    mst_edges: list[tuple[str, str, float]] = []
    total_minutes = 0.0

    for edge in graph.get(start_id, []):
        heappush(queue, (edge.travel_minutes, start_id, edge.target_id))

    while queue and len(visited) < len(graph):
        minutes, source_id, target_id = heappop(queue)
        if target_id in visited:
            continue
        visited.add(target_id)
        total_minutes += minutes
        mst_edges.append((source_id, target_id, minutes))

        for edge in graph.get(target_id, []):
            if edge.target_id not in visited:
                heappush(queue, (edge.travel_minutes, target_id, edge.target_id))

    return total_minutes, mst_edges


def floyd_warshall(graph: Graph) -> dict[str, dict[str, float]]:
    """
    Floyd-Warshall All-Pairs Shortest Path in O(V^3).
    """
    node_ids = list(graph)
    distances = {
        source_id: {
            target_id: 0.0 if source_id == target_id else inf
            for target_id in node_ids
        }
        for source_id in node_ids
    }

    for source_id, edges in graph.items():
        for edge in edges:
            distances[source_id][edge.target_id] = min(
                distances[source_id][edge.target_id],
                edge.travel_minutes,
            )

    for intermediate in node_ids:
        for source in node_ids:
            for target in node_ids:
                through_intermediate = distances[source][intermediate] + distances[intermediate][target]
                if through_intermediate < distances[source][target]:
                    distances[source][target] = through_intermediate

    return distances


def average_shortest_path_minutes(distances: dict[str, dict[str, float]]) -> float:
    values = [
        minutes
        for source_id, targets in distances.items()
        for target_id, minutes in targets.items()
        if source_id != target_id and minutes < inf
    ]
    return sum(values) / len(values) if values else 0.0


def reconstruct_path(previous: dict[str, str | None], end_id: str) -> list[str]:
    path = []
    current = end_id
    while current is not None:
        path.append(current)
        current = previous.get(current)
    return path[::-1]
