from collections import OrderedDict
from threading import Lock
from typing import Any, Hashable


class LRUCache:
    """O(1) get/put cache with least-recently-used eviction."""

    def __init__(self, capacity: int = 8):
        self.capacity = max(1, capacity)
        self._data: OrderedDict[Hashable, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._lock = Lock()

    def get(self, key: Hashable) -> Any | None:
        with self._lock:
            if key not in self._data:
                self.misses += 1
                return None
            self.hits += 1
            self._data.move_to_end(key)
            return self._data[key]

    def put(self, key: Hashable, value: Any) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = value
            if len(self._data) > self.capacity:
                self._data.popitem(last=False)

    def items(self) -> list[tuple[Hashable, Any]]:
        with self._lock:
            return list(self._data.items())[::-1]

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> dict:
        with self._lock:
            total = self.hits + self.misses
            return {
                "capacity": self.capacity,
                "size": len(self._data),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round((self.hits / total) * 100, 1) if total else 0,
            }
