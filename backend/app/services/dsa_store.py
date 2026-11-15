from algorithms.lru import LRUCache

plan_cache = LRUCache(capacity=10)


def cache_key_for_plan(city: str, mood: str, budget_level: str, currency: str, amount: str, days: str, people: str) -> str:
    return f"{city}|{mood}|{budget_level}|{currency}|{amount}|{days}|{people}"
