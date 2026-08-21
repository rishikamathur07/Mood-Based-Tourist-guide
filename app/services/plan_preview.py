from algorithms.insights import budget_feasibility, top_places_by_score
from algorithms.knapsack import place_from_mapping
from app.models import Place
from app.services.currency import format_money, from_usd, normalize_currency, to_usd
from app.services.dsa_store import cache_key_for_plan, plan_cache
from app.services.ml_models import train_category_model, train_cost_model


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

    key = cache_key_for_plan(city, mood, budget_level, currency, str(num_days), str(num_people))
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
    estimated_cost_usd = float(
        train_cost_model().predict(
            [
                {
                    "num_days": num_days,
                    "num_people": num_people,
                    "mood_preference": mood,
                    "budget_level": budget_level,
                }
            ]
        )[0]
    )

    query = Place.query.filter_by(city=city, mood_tag=mood)
    if budget_level:
        query = query.filter_by(budget_level=budget_level)
    places = [place_from_mapping(place_to_row(place)) for place in query.all()]
    budget_info = budget_feasibility(places, budget_amount_usd)
    top_places = top_places_by_score(places, limit=5)

    result = {
        "preferred_category": category,
        "estimated_total_trip_cost": round(from_usd(estimated_cost_usd, currency), 2),
        "estimated_total_trip_cost_formatted": format_money(estimated_cost_usd, currency),
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
