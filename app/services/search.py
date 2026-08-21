from algorithms.edit_distance import fuzzy_rank
from algorithms.trie import PlaceTrie
from app.models import Place

_place_trie: PlaceTrie | None = None
_place_names: list[tuple[str, int]] | None = None


def build_place_trie() -> PlaceTrie:
    global _place_names
    trie = PlaceTrie()
    names = []
    for place in Place.query.order_by(Place.name.asc()).all():
        trie.insert(place.name, place.id)
        names.append((place.name, place.id))
    _place_names = names
    return trie


def get_place_trie() -> PlaceTrie:
    global _place_trie
    if _place_trie is None:
        _place_trie = build_place_trie()
    return _place_trie


def get_place_names() -> list[tuple[str, int]]:
    global _place_names
    if _place_names is None:
        get_place_trie()
    return _place_names or []


def search_places(query: str, limit: int = 8) -> list[int]:
    trie_ids = get_place_trie().search_prefix(query, limit=limit)
    if trie_ids:
        return trie_ids
    return fuzzy_rank(query, get_place_names(), limit=limit)


def reset_place_trie() -> None:
    global _place_trie, _place_names
    _place_trie = None
    _place_names = None
