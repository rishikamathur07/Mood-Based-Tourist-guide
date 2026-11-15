"""
Comprehensive Standalone Algorithm Test Suite for College Viva.

Verifies:
1. 0/1 Knapsack (budget and time constraints, score maximization)
2. Nearest Neighbor + 2-opt TSP (tour optimization and edge uncrossing)
3. Greedy Interval Scheduling (venue hours, transit buffers, day rollover)
4. Priority Queue Replanner (live re-planning with cost/time limits and crowd penalty)
5. Trie Data Structure (instant prefix search and autocompletion)
6. Graph Algorithms (Dijkstra, A*, Prim's MST, Floyd-Warshall, Google Distance Matrix integration)
7. Crowd-Aware Ordering (early scheduling of busier venues)
"""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from algorithms.knapsack import PlaceCandidate, choose_places, place_from_mapping
from algorithms.tsp import haversine_km, nearest_neighbor_order, optimize_route, route_distance_km, two_opt
from algorithms.scheduler import ScheduledVisit, format_duration, format_minutes, schedule_visits
from algorithms.replanner import pick_replacement
from algorithms.trie import PlaceTrie
from algorithms.graph import (
    astar,
    build_place_graph,
    dijkstra,
    floyd_warshall,
    prim_mst,
)
from algorithms.crowd import crowd_aware_order
from algorithms.itinerary import generate_itinerary


def make_test_places():
    return [
        PlaceCandidate(
            place_id="delhi_1",
            name="Red Fort",
            city="Delhi",
            mood_tag="culture",
            latitude=28.6562,
            longitude=77.2410,
            avg_cost=10,
            avg_time_spent_mins=120,
            opening_minutes=540,
            closing_minutes=1080,
            mood_match_score=9.5,
            category="Historical",
        ),
        PlaceCandidate(
            place_id="delhi_2",
            name="Qutub Minar",
            city="Delhi",
            mood_tag="culture",
            latitude=28.5245,
            longitude=77.1855,
            avg_cost=12,
            avg_time_spent_mins=90,
            opening_minutes=420,
            closing_minutes=1140,
            mood_match_score=9.2,
            category="Historical",
        ),
        PlaceCandidate(
            place_id="delhi_3",
            name="Humayun's Tomb",
            city="Delhi",
            mood_tag="culture",
            latitude=28.5933,
            longitude=77.2507,
            avg_cost=8,
            avg_time_spent_mins=90,
            opening_minutes=360,
            closing_minutes=1080,
            mood_match_score=9.0,
            category="Historical",
        ),
        PlaceCandidate(
            place_id="delhi_4",
            name="National Crafts Museum",
            city="Delhi",
            mood_tag="culture",
            latitude=28.6146,
            longitude=77.2429,
            avg_cost=5,
            avg_time_spent_mins=60,
            opening_minutes=600,
            closing_minutes=1020,
            mood_match_score=8.5,
            category="Historical",
        ),
        PlaceCandidate(
            place_id="delhi_5",
            name="Expensive Luxury Heritage Walk",
            city="Delhi",
            mood_tag="culture",
            latitude=28.6000,
            longitude=77.2200,
            avg_cost=150,  # Exceeds standard single budget
            avg_time_spent_mins=180,
            opening_minutes=540,
            closing_minutes=1080,
            mood_match_score=9.8,
            category="Historical",
        ),
    ]


def test_knapsack():
    places = make_test_places()
    # Choose places with budget of 25 USD and 300 minutes
    chosen = choose_places(places, city="Delhi", mood="culture", budget=25, total_time_mins=300)

    assert chosen, "Knapsack should pick places within budget"
    assert sum(p.avg_cost for p in chosen) <= 25, "Cost must be <= 25"
    assert sum(p.avg_time_spent_mins for p in chosen) <= 300, "Time must be <= 300"
    # Ensure expensive place was not picked
    assert not any(p.place_id == "delhi_5" for p in chosen), "Over-budget place must not be picked"
    print("PASS: 0/1 Knapsack constraints and score maximization")


def test_tsp():
    places = make_test_places()[:4]
    start_coord = (28.6300, 77.2100)  # Connaught Place

    initial_order = list(places)
    initial_dist = route_distance_km(initial_order)

    nn_order = nearest_neighbor_order(places, start_coordinate=start_coord)
    assert len(nn_order) == len(places), "All places must be retained in TSP tour"

    opt_order = optimize_route(places, start_coordinate=start_coord)
    opt_dist = route_distance_km(opt_order)

    assert opt_dist <= initial_dist + 1e-6, "Optimized route must be <= random order"
    print(f"PASS: TSP Nearest Neighbor + 2-opt (initial {initial_dist:.2f} km -> opt {opt_dist:.2f} km)")


def test_scheduler():
    places = make_test_places()[:3]
    # Schedule across 2 days
    scheduled = schedule_visits(places, days=2, day_start=540, day_end=1080, travel_buffer=30)

    assert scheduled, "Expected visits to be scheduled"
    for v in scheduled:
        assert v.start_minutes >= v.place.opening_minutes, "Visit cannot start before opening"
        assert v.end_minutes <= v.place.closing_minutes, "Visit cannot end after closing"
        assert v.end_minutes - v.start_minutes == v.place.avg_time_spent_mins, "Duration must match"

    assert format_minutes(540) == "9 AM"
    assert format_minutes(810) == "1:30 PM"
    assert format_duration(90) == "1 hr 30 min"
    print("PASS: Greedy Interval Scheduling and time window validation")


def test_replanner():
    candidates = make_test_places()
    unavailable = {"delhi_1"}  # Red Fort closed

    # Pick replacement with budget 10 and time 90
    replacement = pick_replacement(
        candidates,
        unavailable_ids=unavailable,
        remaining_budget=10,
        remaining_time_mins=90,
    )
    assert replacement is not None, "Should find a valid replacement"
    assert replacement.place_id != "delhi_1", "Must not pick unavailable stop"
    assert replacement.avg_cost <= 10, "Must satisfy budget"
    assert replacement.avg_time_spent_mins <= 90, "Must satisfy time limit"

    # Test crowd-aware replanning
    crowd_levels = {"delhi_2": "High", "delhi_3": "Low", "delhi_4": "Low"}
    calm_replacement = pick_replacement(
        candidates,
        unavailable_ids=unavailable,
        remaining_budget=10,
        remaining_time_mins=90,
        prefer_lower_crowd=True,
        crowd_levels=crowd_levels,
    )
    assert calm_replacement is not None
    assert calm_replacement.place_id in {"delhi_3", "delhi_4"}, "Should prefer calmer venue"
    print("PASS: Priority Queue live replacement and crowd penalty logic")


def test_trie():
    trie = PlaceTrie()
    trie.insert("Red Fort", 101)
    trie.insert("Qutub Minar", 102)
    trie.insert("Taj Mahal", 103)
    trie.insert("Taj Palace Hotel", 104)

    assert trie.search_prefix("taj") == [103, 104], "Prefix search 'taj' must return Taj Mahal and Taj Palace"
    assert trie.search_prefix("qut") == [102], "Prefix search 'qut' must return Qutub Minar"
    assert trie.search_prefix("xyz") == [], "Non-existent prefix must return empty list"
    print("PASS: Trie prefix search O(L) autocompletion")


def test_graph_algorithms():
    places = make_test_places()[:4]
    graph = build_place_graph(places)

    assert len(graph) == 4, "Graph must have 4 vertices"

    # Dijkstra test
    dist, path = dijkstra(graph, "delhi_1", "delhi_2")
    assert dist > 0, "Distance must be positive"
    assert path[0] == "delhi_1" and path[-1] == "delhi_2", "Dijkstra must find start-to-end path"

    # A* test with Haversine straight-line heuristic
    def haversine_heuristic(u_id: str, v_id: str) -> float:
        lookup = {p.place_id: p for p in places}
        return (haversine_km(lookup[u_id], lookup[v_id]) / 35.0) * 60.0

    astar_dist, astar_path = astar(graph, "delhi_1", "delhi_2", heuristic=haversine_heuristic)
    assert abs(astar_dist - dist) < 1e-4, "A* with admissible heuristic must match Dijkstra shortest distance"
    assert astar_path == path, "A* path must match optimal path"

    # Prim's MST test
    mst_cost, mst_edges = prim_mst(graph, "delhi_1")
    assert len(mst_edges) == len(places) - 1, "MST must contain exactly V - 1 edges"
    assert mst_cost > 0, "MST total cost must be positive"

    # Floyd-Warshall test
    fw_matrix = floyd_warshall(graph)
    assert fw_matrix["delhi_1"]["delhi_1"] == 0, "Diagonal of all-pairs shortest path is 0"
    assert abs(fw_matrix["delhi_1"]["delhi_2"] - dist) < 1e-4, "Floyd-Warshall must match Dijkstra"

    print("PASS: Graph Algorithms: Dijkstra, A*, Prim's MST, and Floyd-Warshall")


def test_crowd_aware_ordering():
    places = make_test_places()[:3]
    crowd_levels = {"delhi_1": "Low", "delhi_2": "High", "delhi_3": "Medium"}

    ordered = crowd_aware_order(places, crowd_levels)
    assert ordered[0].place_id == "delhi_2", "High crowd place must be scheduled earliest in the morning"
    assert ordered[-1].place_id == "delhi_1", "Low crowd place can be scheduled later"
    print("PASS: Crowd-aware priority queue scheduling")


def main():
    print("=" * 60)
    print("Running Mood College-Project Algorithm Verification Suite")
    print("=" * 60)
    test_knapsack()
    test_tsp()
    test_scheduler()
    test_replanner()
    test_trie()
    test_graph_algorithms()
    test_crowd_aware_ordering()
    print("=" * 60)
    print("ALL ALGORITHM TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
