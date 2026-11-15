from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from algorithms.insights import budget_feasibility, top_places_by_score
from algorithms.kdtree import build_kdtree, nearest_places
from algorithms.knapsack import place_from_mapping
from algorithms.scheduler import format_duration, format_minutes
from app.auth.routes import login_required
from app.extensions import db
from app.models import Favourite, Place, Trip
from app.services.currency import format_money, normalize_currency, to_usd
from app.services.place_catalog import trusted_city_places
from app.services.search import search_places
from app.trips.routes import place_to_algorithm_row

tools_bp = Blueprint("tools", __name__)


def _trip_summary(trip):
    total_cost = sum(stop.place.avg_cost for stop in trip.itinerary_stops)
    total_time = sum(stop.place.avg_time_spent_mins for stop in trip.itinerary_stops)
    currency = normalize_currency(getattr(trip, "currency", None) or "INR")
    return {
        "trip": trip,
        "stops": len(trip.itinerary_stops),
        "total_cost_label": format_money(total_cost, currency),
        "total_time_label": format_duration(total_time),
        "currency": currency,
    }


@tools_bp.route("/")
@login_required
def index():
    trip_count = Trip.query.filter_by(user_id=g.user.id).count()
    favourite_count = Favourite.query.filter_by(user_id=g.user.id).count()
    return render_template(
        "tools/index.html",
        trip_count=trip_count,
        favourite_count=favourite_count,
    )


@tools_bp.route("/discover")
@login_required
def discover():
    cities = [row[0] for row in db.session.query(Place.city).distinct().order_by(Place.city).all()]
    moods = [row[0] for row in db.session.query(Place.mood_tag).distinct().order_by(Place.mood_tag).all()]

    city = request.args.get("city", "")
    mood = request.args.get("mood", "")
    query = request.args.get("q", "").strip()

    places = []
    if city and mood:
        base_query = Place.query.filter_by(city=city, mood_tag=mood)
        if query:
            place_ids = search_places(query, limit=30)
            if place_ids:
                id_set = set(place_ids)
                places = [place for place in base_query.all() if place.id in id_set]
                places.sort(key=lambda place: place_ids.index(place.id) if place.id in place_ids else 999)
        else:
            candidates = [place_from_mapping(place_to_algorithm_row(place)) for place in base_query.all()]
            ranked = top_places_by_score(candidates, limit=24)
            lookup = {place.place_id: place for place in base_query.all()}
            places = [lookup[candidate.place_id] for candidate in ranked if candidate.place_id in lookup]

    favourite_ids = {
        favourite.place_id for favourite in Favourite.query.filter_by(user_id=g.user.id).all()
    }

    return render_template(
        "tools/discover.html",
        cities=cities,
        moods=moods,
        city=city,
        mood=mood,
        query=query,
        places=places,
        favourite_ids=favourite_ids,
    )


@tools_bp.route("/compare")
@login_required
def compare():
    trips = Trip.query.filter_by(user_id=g.user.id).order_by(Trip.created_at.desc()).all()
    left_id = request.args.get("left", type=int)
    right_id = request.args.get("right", type=int)

    left = Trip.query.filter_by(id=left_id, user_id=g.user.id).first() if left_id else None
    right = Trip.query.filter_by(id=right_id, user_id=g.user.id).first() if right_id else None

    if left and right and left.id == right.id:
        right = None

    summaries = []
    if left:
        summaries.append(_trip_summary(left))
    if right:
        summaries.append(_trip_summary(right))

    return render_template(
        "tools/compare.html",
        trips=trips,
        left=left,
        right=right,
        summaries=summaries,
    )


@tools_bp.route("/nearby")
@login_required
def nearby():
    trips = Trip.query.filter_by(user_id=g.user.id).order_by(Trip.created_at.desc()).all()
    trip_id = request.args.get("trip_id", type=int)
    stop_id = request.args.get("stop_id", type=int)

    selected_trip = None
    selected_stop = None
    alternatives = []

    if trip_id:
        selected_trip = Trip.query.filter_by(id=trip_id, user_id=g.user.id).first()
    elif trips:
        selected_trip = trips[0]

    if selected_trip and selected_trip.itinerary_stops:
        if stop_id:
            selected_stop = next(
                (stop for stop in selected_trip.itinerary_stops if stop.id == stop_id),
                None,
            )
        if selected_stop is None:
            selected_stop = selected_trip.itinerary_stops[0]

        blocked_ids = {stop.place.place_id for stop in selected_trip.itinerary_stops}
        catalog = trusted_city_places(
            Place.query.filter_by(city=selected_trip.city, mood_tag=selected_trip.mood)
            .filter(Place.category != "Hotel")
            .all()
        )
        candidates = [
            place_from_mapping(place_to_algorithm_row(place))
            for place in catalog
            if place.place_id not in blocked_ids
        ]
        anchor = place_from_mapping(place_to_algorithm_row(selected_stop.place))
        tree = build_kdtree(candidates)
        for distance, place in nearest_places(tree, anchor, limit=8, blocked_ids=blocked_ids):
            alternatives.append(
                {
                    "place_id": next(item.id for item in catalog if item.place_id == place.place_id),
                    "name": place.name,
                    "category": place.category,
                    "distance_km": round(distance, 2),
                    "score": place.mood_match_score,
                    "cost": place.avg_cost,
                    "time": place.avg_time_spent_mins,
                }
            )

    currency = normalize_currency(getattr(selected_trip, "currency", None) or "INR") if selected_trip else "INR"

    return render_template(
        "tools/nearby.html",
        trips=trips,
        selected_trip=selected_trip,
        selected_stop=selected_stop,
        alternatives=alternatives,
        format_money=format_money,
        currency=currency,
        format_duration=format_duration,
    )


@tools_bp.route("/budget")
@login_required
def budget():
    cities = [row[0] for row in db.session.query(Place.city).distinct().order_by(Place.city).all()]
    moods = [row[0] for row in db.session.query(Place.mood_tag).distinct().order_by(Place.mood_tag).all()]

    city = request.args.get("city", "")
    mood = request.args.get("mood", "")
    currency = normalize_currency(request.args.get("currency", "INR"))
    try:
        budget_local = float(request.args.get("amount", "0") or 0)
    except ValueError:
        budget_local = 0

    budget_info = None
    affordable_places = []
    if city and mood and budget_local > 0:
        budget_usd = int(to_usd(budget_local, currency))
        rows = Place.query.filter_by(city=city, mood_tag=mood).all()
        candidates = [place_from_mapping(place_to_algorithm_row(place)) for place in rows]
        budget_info = budget_feasibility(candidates, budget_usd)
        affordable_places = [
            place
            for place in rows
            if int(place.avg_cost) <= budget_usd
        ]
        affordable_places.sort(key=lambda place: place.mood_match_score, reverse=True)
        affordable_places = affordable_places[:12]

    return render_template(
        "tools/budget.html",
        cities=cities,
        moods=moods,
        city=city,
        mood=mood,
        currency=currency,
        budget_amount=budget_local,
        budget_info=budget_info,
        affordable_places=affordable_places,
        format_money=format_money,
        format_duration=format_duration,
    )


@tools_bp.route("/favourites")
@login_required
def favourites():
    favourites_list = (
        Favourite.query.filter_by(user_id=g.user.id)
        .order_by(Favourite.created_at.desc())
        .all()
    )

    grouped = {}
    for favourite in favourites_list:
        city = favourite.place.city
        grouped.setdefault(city, []).append(favourite)

    return render_template("tools/favourites.html", grouped=grouped, total=len(favourites_list))


@tools_bp.route("/favourites/<int:favourite_id>/remove", methods=["POST"])
@login_required
def remove_favourite(favourite_id):
    favourite = Favourite.query.filter_by(id=favourite_id, user_id=g.user.id).first_or_404()
    db.session.delete(favourite)
    db.session.commit()
    flash("Removed from favourites.", "info")
    return redirect(url_for("tools.favourites"))


@tools_bp.route("/hotels")
@login_required
def hotels():
    cities = [row[0] for row in db.session.query(Place.city).distinct().order_by(Place.city).all()]
    latest_trip = Trip.query.filter_by(user_id=g.user.id).order_by(Trip.created_at.desc()).first()
    default_city = latest_trip.city if latest_trip else (cities[0] if cities else "Delhi")
    city = request.args.get("city", default_city)
    budget = request.args.get("budget", "").strip().capitalize()
    query = request.args.get("q", "").strip()
    currency = normalize_currency(request.args.get("currency", (latest_trip.currency if latest_trip else "INR")))

    hotel_query = Place.query.filter_by(city=city, category="Hotel")
    if budget in {"Low", "Medium", "High"}:
        hotel_query = hotel_query.filter_by(budget_level=budget)
    if query:
        hotel_query = hotel_query.filter(Place.name.ilike(f"%{query}%"))

    hotels_list = hotel_query.order_by(Place.avg_cost.asc()).all()
    return render_template(
        "tools/hotels.html",
        cities=cities,
        city=city,
        budget=budget,
        query=query,
        currency=currency,
        hotels=hotels_list,
        format_money=format_money,
    )

