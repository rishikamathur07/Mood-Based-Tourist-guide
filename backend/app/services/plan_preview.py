from algorithms.insights import budget_feasibility, top_places_by_score
from algorithms.itinerary import generate_itinerary
from algorithms.knapsack import place_from_mapping
from app.models import Place
from app.services.currency import format_money, from_usd, normalize_currency, to_usd
from app.services.dsa_store import cache_key_for_plan, plan_cache
from app.services.ml_models import train_category_model
from app.services.place_catalog import trusted_city_places
from app.services.trip_budget import calculate_local_trip_budget


def _representative_daily_attraction_cost(places: list, days: int) -> float:
    """Estimate a sensible ticket allowance without using a user-entered cap."""
    if not places:
        return 0.0
    costs = sorted(float(place.avg_cost) for place in places)
    durations = sorted(max(30, int(place.avg_time_spent_mins)) for place in places)
    median_cost = costs[len(costs) // 2]
    median_duration = durations[len(durations) // 2]
    stops_per_day = max(1, min(3, 480 // median_duration))
    return median_cost * stops_per_day * days


def build_budget_suggestions(payload: dict) -> dict:
    """Return local-trip defaults that scale with the group and trip duration."""
    city = payload["city"]
    mood = payload["mood_preference"]
    currency = normalize_currency(payload.get("currency", "INR"))
    num_days = int(payload["num_days"])
    num_people = int(payload["num_people"])

    city_candidates = trusted_city_places(
        Place.query.filter_by(city=city).filter(Place.category != "Hotel").all()
    )
    mood_candidates = [place for place in city_candidates if place.mood_tag.casefold() == mood.casefold()]
    all_candidates = mood_candidates or city_candidates
    hotels = trusted_city_places(Place.query.filter_by(city=city, category="Hotel").all())
    suggestions = {}

    for level in ("Low", "Medium", "High"):
        level_candidates = [place for place in all_candidates if place.budget_level == level]
        attraction_cost = _representative_daily_attraction_cost(level_candidates or all_candidates, num_days)
        estimate = calculate_local_trip_budget(
            budget_level=level,
            num_days=num_days,
            num_people=num_people,
            attraction_cost=attraction_cost,
            hotels=hotels,
        )["total"]
        local_amount = from_usd(estimate, currency)
        rounding = 100 if currency == "INR" else 5
        suggestions[level] = max(rounding, int(round(local_amount / rounding) * rounding))

    return {"currency": currency, "suggestions": suggestions}


def place_to_row(place):
    return {
        "place_id": place.place_id,
        "name": place.name,
        "city": place.city,
        "mood_tag": place.mood_tag,
        "category": place.category,
        "latitude": place.latitude,
        "longitude": place.longitude,
        "avg_cost": place.avg_cost,
        "avg_time_spent_mins": place.avg_time_spent_mins,
        "opening_minutes": place.opening_minutes,
        "closing_minutes": place.closing_minutes,
        "mood_match_score": place.mood_match_score,
    }


def build_plan_preview(payload: dict, use_cache: bool = True) -> dict:
    city = payload["city"]
    mood = payload["mood_preference"]
    budget_level = payload["budget_level"]
    currency = normalize_currency(payload.get("currency", "INR"))
    budget_amount_local = float(payload["budget_amount"])
    num_days = int(payload["num_days"])
    num_people = int(payload["num_people"])
    budget_amount_usd = int(to_usd(budget_amount_local, currency))

    key = cache_key_for_plan(city, mood, budget_level, currency, str(budget_amount_local), str(num_days), str(num_people))
    if use_cache:
        cached = plan_cache.get(key)
        if cached is not None:
            result = dict(cached)
            result["cache"] = "hit"
            return result

    category = train_category_model().predict(
        [
            {
                "city": city,
                "num_days": num_days,
                "num_people": num_people,
                "mood_preference": mood,
                "budget_level": budget_level,
            }
        ]
    )[0]
    city_places = trusted_city_places(
        Place.query.filter_by(city=city).filter(Place.category != "Hotel").all()
    )
    mood_places = [place for place in city_places if place.mood_tag.casefold() == mood.casefold()]
    catalog_places = mood_places or city_places
    budget_matches = [place for place in catalog_places if place.budget_level == budget_level]
    if budget_matches:
        catalog_places = budget_matches
    places = [place_from_mapping({**place_to_row(place), "mood_tag": mood}) for place in catalog_places]
    budget_info = budget_feasibility(places, budget_amount_usd)
    top_places = top_places_by_score(places, limit=5)
    scheduled = generate_itinerary(
        [{**place_to_row(place), "mood_tag": mood} for place in catalog_places],
        city=city,
        mood=mood,
        budget=budget_amount_usd,
        days=num_days,
    )
    attraction_cost = sum(visit.place.avg_cost for visit in scheduled)
    hotels = trusted_city_places(Place.query.filter_by(city=city, category="Hotel").all())
    local_budget = calculate_local_trip_budget(
        budget_level=budget_level,
        num_days=num_days,
        num_people=num_people,
        attraction_cost=attraction_cost,
        hotels=hotels,
    )
    local_budget["difference"] = round(budget_amount_usd - local_budget["total"], 2)
    local_budget["over_budget"] = local_budget["difference"] < 0

    result = {
        "preferred_category": category,
        "local_budget": {
            **local_budget,
            "total_formatted": format_money(local_budget["total"], currency),
            "difference_formatted": format_money(abs(local_budget["difference"]), currency),
        },
        "currency": currency,
        "budget": {
            **budget_info,
            "average_cost_formatted": format_money(budget_info["average_cost"], currency),
        },
        "top_places": [
            {
                "name": place.name,
                "score": place.mood_match_score,
                "cost_formatted": format_money(place.avg_cost, currency),
            }
            for place in top_places
        ],
        "cache": "miss",
    }
    if use_cache:
        plan_cache.put(key, {k: v for k, v in result.items() if k != "cache"})
    return result
