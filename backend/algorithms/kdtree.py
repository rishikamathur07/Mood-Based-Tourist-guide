from dataclasses import dataclass
from math import inf
from typing import Sequence

from algorithms.knapsack import PlaceCandidate
from algorithms.tsp import haversine_km


@dataclass
class KDNode:
    place: PlaceCandidate
    axis: int
    left: "KDNode | None" = None
    right: "KDNode | None" = None


def build_kdtree(places: Sequence[PlaceCandidate], depth: int = 0) -> KDNode | None:
    if not places:
        return None

    axis = depth % 2
    sorted_places = sorted(places, key=lambda place: (place.latitude, place.longitude)[axis])
    median = len(sorted_places) // 2

    # KD-tree reasoning:
    # Latitude and longitude form a 2D search space. Splitting by alternating
    # axes creates a tree that quickly ignores far-away branches during nearest
    # neighbour lookup.
    return KDNode(
        place=sorted_places[median],
        axis=axis,
        left=build_kdtree(sorted_places[:median], depth + 1),
        right=build_kdtree(sorted_places[median + 1 :], depth + 1),
    )


def nearest_places(
    root: KDNode | None,
    target: PlaceCandidate,
    limit: int = 3,
    blocked_ids: set[str] | None = None,
) -> list[tuple[float, PlaceCandidate]]:
    blocked_ids = blocked_ids or set()
    best: list[tuple[float, PlaceCandidate]] = []

    def add_candidate(place: PlaceCandidate) -> None:
        if place.place_id in blocked_ids:
            return
        distance = haversine_km(target, place)
        best.append((distance, place))
        best.sort(key=lambda item: item[0])
        del best[limit:]

    def farthest_best_distance() -> float:
        if len(best) < limit:
            return inf
        return best[-1][0]

    def search(node: KDNode | None) -> None:
        if node is None:
            return

        add_candidate(node.place)
        target_value = (target.latitude, target.longitude)[node.axis]
        node_value = (node.place.latitude, node.place.longitude)[node.axis]
        near_branch = node.left if target_value < node_value else node.right
        far_branch = node.right if target_value < node_value else node.left

        search(near_branch)

        axis_gap_km = abs(target_value - node_value) * 111
        if axis_gap_km <= farthest_best_distance():
            search(far_branch)

    search(root)
    return best
