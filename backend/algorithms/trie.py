"""
Trie (Prefix Tree) Module for Fast Auto-Complete Place Name Search.

College Viva Summary:
---------------------
1. Problem:
   In interactive tourist guide apps, users type venue or attraction names into a search
   box. Linear scanning of thousands of database rows for every keystroke (e.g. `LIKE '%query%'`)
   incurs O(N * M) query overhead and database disk I/O.

2. Data Structure:
   - Trie (Retrieval / Prefix Tree).
   - Each node contains a character mapping: `children: dict[str, TrieNode]`.
   - Each node maintains a list of `place_ids` matching words having that prefix.
   - `is_word`: Boolean flag marking the end of a valid attraction title.

3. Performance:
   - Insertion Time: O(L) where L is the character length of the attraction name.
   - Lookup / Search Time: O(K) where K is the prefix length (e.g., typing 'taj' takes exactly 3 steps).
   - Independent of the total number of places (N) in the database.
"""

from dataclasses import dataclass, field


@dataclass
class TrieNode:
    children: dict[str, "TrieNode"] = field(default_factory=dict)
    place_ids: list[int] = field(default_factory=list)
    is_word: bool = False


class PlaceTrie:
    """In-memory Trie for instant prefix search on tourist place names."""

    def __init__(self):
        self.root = TrieNode()

    def insert(self, name: str, place_id: int) -> None:
        """
        Insert an attraction name into the Trie and index place_id along the path.
        """
        node = self.root
        for character in name.lower():
            node = node.children.setdefault(character, TrieNode())
            node.place_ids.append(place_id)
        node.is_word = True

    def search_prefix(self, prefix: str, limit: int = 8) -> list[int]:
        """
        Search for place IDs matching the prefix string in O(length of prefix).
        """
        node = self.root
        for character in prefix.lower():
            if character not in node.children:
                return []
            node = node.children[character]

        # Preserve insertion order while filtering duplicates
        seen = set()
        results = []
        for place_id in node.place_ids:
            if place_id not in seen:
                results.append(place_id)
                seen.add(place_id)
            if len(results) == limit:
                break
        return results
