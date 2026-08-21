from dataclasses import dataclass, field


@dataclass
class TrieNode:
    children: dict[str, "TrieNode"] = field(default_factory=dict)
    place_ids: list[int] = field(default_factory=list)
    is_word: bool = False


class PlaceTrie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, name: str, place_id: int) -> None:
        node = self.root
        for character in name.lower():
            node = node.children.setdefault(character, TrieNode())
            node.place_ids.append(place_id)
        node.is_word = True

    def search_prefix(self, prefix: str, limit: int = 8) -> list[int]:
        node = self.root
        for character in prefix.lower():
            if character not in node.children:
                return []
            node = node.children[character]

        # The trie narrows suggestions in O(length of prefix), then returns
        # IDs collected under that prefix. This is faster than scanning every
        # place name for every keypress.
        seen = set()
        results = []
        for place_id in node.place_ids:
            if place_id not in seen:
                results.append(place_id)
                seen.add(place_id)
            if len(results) == limit:
                break
        return results
