"""Transparent local-trip budget calculation used in the traveller UI."""

from math import ceil


DAILY_COSTS = {
    "Low": {"food": 8, "transport": 5},
    "Medium": {"food": 14, "transport": 10},
    "High": {"food": 25, "transport": 18},
}


def calculate_local_trip_budget(
    *,
    budget_level: str,
    num_days: int,
    num_people: int,
    attraction_cost: float,
    hotels: list,
) -> dict:
    """Estimate costs shown to travellers without claiming flight prices.

    The estimate uses selected attraction prices, the lowest nightly hotel in
    the chosen budget category, food per person per day, and local transport
    per person per day. Flights are intentionally excluded because they change
    with route and date and are not part of the local project dataset.
    """
    level = budget_level if budget_level in DAILY_COSTS else "Medium"
    daily = DAILY_COSTS[level]
    nights = max(0, num_days - 1)
    rooms = max(1, ceil(num_people / 2))
    matching_hotels = [hotel for hotel in hotels if hotel.budget_level == level]
    selected_hotel = min(matching_hotels or hotels, key=lambda hotel: hotel.avg_cost, default=None)
    stay_cost = (selected_hotel.avg_cost * nights * rooms) if selected_hotel else 0
    food_cost = daily["food"] * num_days * num_people
    transport_cost = daily["transport"] * num_days * num_people
    total = attraction_cost + stay_cost + food_cost + transport_cost

    return {
        "attractions": round(attraction_cost, 2),
        "stay": round(stay_cost, 2),
        "food": round(food_cost, 2),
        "transport": round(transport_cost, 2),
        "total": round(total, 2),
        "nights": nights,
        "rooms": rooms,
        "hotel_name": selected_hotel.name if selected_hotel else None,
    }
