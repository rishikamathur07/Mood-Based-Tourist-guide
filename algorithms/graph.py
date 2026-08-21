from dataclasses import dataclass
from heapq import heappop, heappush
from math import inf
from typing import Callable, Iterable

from algorithms.knapsack import PlaceCandidate
from algorithms.tsp import haversine_km


@dataclass(frozen=True)
class Edge:
    target_id: str
    distance_km: float
    travel_minutes: float


Graph = dict[str, list[Edge]]


def estimate_travel_minutes(distance_km: float, average_speed_kmph: float = 28) -> float:
    return (distance_km / average_speed_kmph) * 60


def build_place_graph(places: Iterable[PlaceCandidate]) -> Graph:
    nodes = list(places)
    graph: Graph = {place.place_id: [] for place in nodes}

    # Graph model for viva:
    # Each selected place is a node. Every pair of places gets a weighted edge.
    # The edge weight is estimated travel time, derived from Haversine distance.
    # Later, Google Distance Matrix can replace this estimated weight with live traffic time.
    for source in nodes:
        for target in nodes:
            if source.place_id == target.place_id:
                continue
            distance = haversine_km(source, target)
            graph[source.place_id].append(
                Edge(
                    target_id=target.place_id,
                    distance_km=distance,
                    travel_minutes=estimate_travel_minutes(distance),
                )
            )

    return graph


def dijkstra(graph: Graph, start_id: str, end_id: str) -> tuple[float, list[str]]:
    distances = {node_id: inf for node_id in graph}
    previous: dict[str, str | None] = {node_id: None for node_id in graph}
    distances[start_id] = 0
    queue: list[tuple[float, str]] = [(0, start_id)]

    # Dijkstra always expands the currently cheapest known node first.
    # Because all travel times are non-negative, once the destination is popped,
    # the shortest path to it is final.
    while queue:
        current_distance, current_id = heappop(queue)
        if current_distance > distances[current_id]:
            continue
        if current_id == end_id:
            break

        for edge in graph[current_id]:
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
    g_score = {node_id: inf for node_id in graph}
    previous: dict[str, str | None] = {node_id: None for node_id in graph}
    g_score[start_id] = 0
    queue: list[tuple[float, str]] = [(heuristic(start_id, end_id), start_id)]

    # A* is Dijkstra plus a heuristic. Here the heuristic can be straight-line
    # travel time, so nodes geographically closer to the destination are tried
    # earlier while still returning the shortest path when the heuristic is admissible.
    while queue:
        _, current_id = heappop(queue)
        if current_id == end_id:
            break

        for edge in graph[current_id]:
            tentative = g_score[current_id] + edge.travel_minutes
            if tentative < g_score[edge.target_id]:
                previous[edge.target_id] = current_id
                g_score[edge.target_id] = tentative
                f_score = tentative + heuristic(edge.target_id, end_id)
                heappush(queue, (f_score, edge.target_id))

    return g_score[end_id], reconstruct_path(previous, end_id)


def prim_mst(graph: Graph, start_id: str) -> tuple[float, list[tuple[str, str, float]]]:
    visited = {start_id}
    queue: list[tuple[float, str, str]] = []
    mst_edges: list[tuple[str, str, float]] = []
    total_minutes = 0.0

    # Prim's MST reasoning:
    # Instead of finding one route order, MST finds the cheapest set of edges
    # that keeps every selected place connected. It is useful for explaining a
    # compact "navigation network" on the map without unnecessary extra edges.
    for edge in graph[start_id]:
        heappush(queue, (edge.travel_minutes, start_id, edge.target_id))

    while queue and len(visited) < len(graph):
        minutes, source_id, target_id = heappop(queue)
        if target_id in visited:
            continue
        visited.add(target_id)
        total_minutes += minutes
        mst_edges.append((source_id, target_id, minutes))

        for edge in graph[target_id]:
            if edge.target_id not in visited:
                heappush(queue, (edge.travel_minutes, target_id, edge.target_id))

    return total_minutes, mst_edges


def floyd_warshall(graph: Graph) -> dict[str, dict[str, float]]:
    node_ids = list(graph)
    distances = {
        source_id: {
            target_id: 0 if source_id == target_id else inf
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

    # Floyd-Warshall reasoning:
    # Try every node as an intermediate stop between every pair of nodes.
    # If going source -> intermediate -> target is cheaper, update the answer.
    # This gives all-pairs shortest travel estimates in O(V^3).
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
    return sum(values) / len(values) if values else 0


def reconstruct_path(previous: dict[str, str | None], end_id: str) -> list[str]:
    path = []
    current = end_id
    while current is not None:
        path.append(current)
        current = previous.get(current)
    return path[::-1]
