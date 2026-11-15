from bisect import bisect_right
from collections import Counter
from heapq import nlargest
from statistics import mean

from algorithms.knapsack import PlaceCandidate


def top_places_by_score(places: list[PlaceCandidate], limit: int = 5) -> list[PlaceCandidate]:
    # Heap reasoning:
    # nlargest internally uses a heap, so we can get the strongest mood-score
    # candidates without fully sorting the dataset. That is useful when the
    # places table grows beyond this college dataset.
    return nlargest(limit, places, key=lambda place: place.mood_match_score)


def budget_feasibility(places: list[PlaceCandidate], budget: int) -> dict:
    costs = sorted(int(place.avg_cost) for place in places)
    affordable_count = bisect_right(costs, budget)

    # Binary search reasoning:
    # The sorted cost list lets us find how many places fit the user's budget in
    # O(log n). A normal scan would be O(n) for every budget change in the UI.
    return {
        "affordable_count": affordable_count,
        "total_count": len(costs),
        "average_cost": round(mean(costs), 2) if costs else 0,
        "median_cost": costs[len(costs) // 2] if costs else 0,
    }


def category_histogram(places: list[PlaceCandidate], limit: int = 4) -> list[dict]:
    """Hash-map frequency count of categories in the filtered place set."""
    counts = Counter(place.category or "Other" for place in places)
    return [{"category": name, "count": count} for name, count in counts.most_common(limit)]


def two_pointer_budget_pairs(places: list[PlaceCandidate], budget: int) -> dict:
    """
    Sort by cost, then use two pointers to count place-pairs that fit the budget together.
    """
    ordered = sorted(places, key=lambda place: place.avg_cost)
    left = 0
    right = len(ordered) - 1
    pair_count = 0
    best = None

    while left < right:
        total = ordered[left].avg_cost + ordered[right].avg_cost
        if total <= budget:
            score = ordered[left].mood_match_score + ordered[right].mood_match_score
            if best is None or score > best["score"]:
                best = {
                    "score": round(score, 2),
                    "left": ordered[left].name,
                    "right": ordered[right].name,
                    "cost": total,
                }
            pair_count += right - left
            left += 1
        else:
            right -= 1

    return {
        "pair_count": pair_count,
        "best_pair": best,
        "budget": budget,
    }
