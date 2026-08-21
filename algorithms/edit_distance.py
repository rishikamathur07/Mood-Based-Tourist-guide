def levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (left_char != right_char)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def fuzzy_rank(query: str, candidates: list[tuple[str, int]], limit: int = 8) -> list[int]:
    """Rank place IDs by edit distance to the query (typo-tolerant search)."""
    needle = query.lower().strip()
    if not needle:
        return []

    scored = []
    for name, place_id in candidates:
        hay = name.lower()
        if needle in hay:
            distance = max(0, len(hay) - len(needle)) // 4
        else:
            distance = levenshtein(needle, hay[: max(len(needle) + 2, len(hay))])
            # Compare against a short prefix to keep fuzzy search responsive.
            distance = min(distance, levenshtein(needle, hay[: len(needle) + 1]))
        scored.append((distance, place_id))

    scored.sort(key=lambda item: item[0])
    results = []
    seen = set()
    for distance, place_id in scored:
        if distance > max(3, len(needle) // 2):
            continue
        if place_id in seen:
            continue
        results.append(place_id)
        seen.add(place_id)
        if len(results) == limit:
            break
    return results
