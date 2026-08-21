from algorithms.tsp import haversine_km


class UnionFind:
    def __init__(self, items: list[str]):
        self.parent = {item: item for item in items}
        self.rank = {item: 0 for item in items}

    def find(self, item: str) -> str:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            self.parent[root_left] = root_right
        elif self.rank[root_left] > self.rank[root_right]:
            self.parent[root_right] = root_left
        else:
            self.parent[root_right] = root_left
            self.rank[root_left] += 1


def cluster_nearby_places(places, radius_km: float = 3.0) -> list[dict]:
    """Group places that are within radius_km of each other using Union-Find."""
    if not places:
        return []

    ids = [place.place_id for place in places]
    uf = UnionFind(ids)
    lookup = {place.place_id: place for place in places}

    for index, left in enumerate(places):
        for right in places[index + 1 :]:
            if haversine_km(left, right) <= radius_km:
                uf.union(left.place_id, right.place_id)

    clusters: dict[str, list] = {}
    for place_id in ids:
        root = uf.find(place_id)
        clusters.setdefault(root, []).append(lookup[place_id])

    ranked = sorted(clusters.values(), key=len, reverse=True)
    return [
        {
            "size": len(group),
            "places": [place.name for place in group[:4]],
            "anchor": group[0].name,
        }
        for group in ranked
        if len(group) >= 2
    ][:3]
