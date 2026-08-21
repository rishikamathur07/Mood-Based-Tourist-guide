def best_mood_window(scores: list[float], window_size: int = 3) -> dict:
    """Sliding window maximum: best consecutive stretch of mood scores."""
    if not scores:
        return {"start": 0, "end": 0, "sum": 0, "average": 0, "size": 0}

    size = max(1, min(window_size, len(scores)))
    window_sum = sum(scores[:size])
    best_sum = window_sum
    best_start = 0

    for index in range(size, len(scores)):
        window_sum += scores[index] - scores[index - size]
        if window_sum > best_sum:
            best_sum = window_sum
            best_start = index - size + 1

    return {
        "start": best_start,
        "end": best_start + size - 1,
        "sum": round(best_sum, 2),
        "average": round(best_sum / size, 2),
        "size": size,
    }
