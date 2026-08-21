from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for

from algorithms.graph import (
    astar,
    average_shortest_path_minutes,
    build_place_graph,
    dijkstra,
    estimate_travel_minutes,
    floyd_warshall,
    prim_mst,
)
from algorithms.itinerary import generate_itinerary
from algorithms.kdtree import build_kdtree, nearest_places
from algorithms.knapsack import place_from_mapping
from algorithms.replanner import pick_replacement
from algorithms.scheduler import format_duration, format_minutes
from algorithms.tsp import haversine_km
from app.auth.routes import login_required
from app.extensions import db
from app.models import Favourite, ItineraryStop, Place, Review, Trip
from app.services.currency import (
    budget_defaults_for,
    currency_symbol,
    format_money,
    from_usd,
    normalize_currency,
    to_usd,
)
from app.services.ml_models import train_category_model, train_cost_model

trips_bp = Blueprint("trips", __name__)

BUDGET_DEFAULTS = {
    "Low": 500,
    "Medium": 1200,
    "High": 2500,
}


def place_to_algorithm_row(place):
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


def google_maps_directions_url(stops):
    if not stops:
        return ""
    points = [
        f"{stop.place.latitude},{stop.place.longitude}"
        for stop in stops
        if stop.place is not None
    ]
    if not points:
        return ""
    origin = points[0]
    destination = points[-1]
    waypoints = "|".join(points[1:-1])
    url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin}&destination={destination}&travelmode=driving"
    )
    if waypoints:
        url += f"&waypoints={waypoints}"
    return url



def save_scheduled_visits(trip, scheduled_visits):
    place_ids = [visit.place.place_id for visit in scheduled_visits]
    places_by_external_id = {
        place.place_id: place
        for place in Place.query.filter(Place.place_id.in_(place_ids)).all()
    }

    for order, visit in enumerate(scheduled_visits, start=1):
        place = places_by_external_id.get(visit.place.place_id)
        if place is None:
            continue

        db.session.add(
            ItineraryStop(
                trip=trip,
                place=place,
                visit_order=order,
                day=visit.day,
                start_minutes=visit.start_minutes,
                end_minutes=visit.end_minutes,
            )
        )


def replace_trip_stops(trip, scheduled_visits):
    ItineraryStop.query.filter_by(trip_id=trip.id).delete()
    save_scheduled_visits(trip, scheduled_visits)


@trips_bp.route("/")
@login_required
def dashboard():
    trips = (
        Trip.query.filter_by(user_id=g.user.id)
        .order_by(Trip.created_at.desc())
        .all()
    )
    return render_template("trips/dashboard.html", trips=trips)


@trips_bp.route("/setup", methods=["GET", "POST"])
@login_required
def setup():
    cities = [
        row[0]
        for row in db.session.query(Place.city)
        .distinct()
        .order_by(Place.city.asc())
        .all()
    ]

    moods = [
        row[0]
        for row in db.session.query(Place.mood_tag)
        .distinct()
        .order_by(Place.mood_tag.asc())
        .all()
    ]

    budget_levels = [
        row[0]
        for row in db.session.query(Place.budget_level)
        .filter(Place.budget_level.isnot(None))
        .distinct()
        .order_by(Place.budget_level.asc())
        .all()
    ]

    selected_currency = normalize_currency(request.form.get("currency") or request.args.get("currency") or "INR")

    def render_setup(**extra):
        return render_template(
            "trips/setup.html",
            cities=cities,
            moods=moods,
            budget_levels=budget_levels,
            budget_defaults=BUDGET_DEFAULTS,
            budget_defaults_inr=budget_defaults_for("INR"),
            currency=extra.get("currency", selected_currency),
            **{k: v for k, v in extra.items() if k != "currency"},
        )

    if request.method == "POST":
        city = request.form.get("city", "").strip()
        mood = request.form.get("mood", "").strip()
        budget_level = request.form.get("budget_level", "").strip()
        budget_amount_raw = request.form.get("budget_amount", "").strip()
        currency = normalize_currency(request.form.get("currency", "USD"))
        num_days_raw = request.form.get("num_days", "1")
        num_people_raw = request.form.get("num_people", "1")

        try:
            num_days = int(num_days_raw)
        except ValueError:
            num_days = 0

        try:
            num_people = int(num_people_raw)
        except ValueError:
            num_people = 0

        try:
            budget_amount_local = float(budget_amount_raw)
        except ValueError:
            budget_amount_local = float(budget_defaults_for(currency).get(budget_level, 1000))

        budget_amount_usd = to_usd(budget_amount_local, currency)

        if not city or not mood or not budget_level or num_days < 1 or num_people < 1 or budget_amount_local <= 0:
            flash("Choose a city, mood, budget, currency, and at least one day.", "danger")
            return render_setup(currency=currency)

        matching_places = Place.query.filter_by(city=city, mood_tag=mood).all()
        if budget_level:
            budget_matches = [place for place in matching_places if place.budget_level == budget_level]
            if budget_matches:
                matching_places = budget_matches

        scheduled_visits = generate_itinerary(
            [place_to_algorithm_row(place) for place in matching_places],
            city=city,
            mood=mood,
            budget=int(budget_amount_usd),
            days=num_days,
        )

        if not scheduled_visits:
            flash("No itinerary could be generated with those choices. Try a higher budget or more days.", "warning")
            return render_setup(currency=currency)

        category_prediction = train_category_model().predict(
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
        cost_prediction = float(
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

        trip = Trip(
            user_id=g.user.id,
            city=city,
            mood=mood,
            budget_level=budget_level,
            budget_amount=round(budget_amount_local, 2),
            currency=currency,
            num_days=num_days,
            num_people=num_people,
            predicted_category=category_prediction,
            estimated_trip_cost=round(from_usd(cost_prediction, currency), 2),
        )
        db.session.add(trip)
        save_scheduled_visits(trip, scheduled_visits)
        db.session.commit()
        flash("Your itinerary is ready.", "success")
        return redirect(url_for("trips.detail", trip_id=trip.id))

    return render_setup(currency=selected_currency)


@trips_bp.route("/<int:trip_id>")
@login_required
def detail(trip_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=g.user.id).first_or_404()
    currency = normalize_currency(getattr(trip, "currency", None) or "USD")
    total_cost_usd = sum(stop.place.avg_cost for stop in trip.itinerary_stops)
    total_time = sum(stop.place.avg_time_spent_mins for stop in trip.itinerary_stops)
    favourite_place_ids = {
        favourite.place_id
        for favourite in Favourite.query.filter_by(user_id=g.user.id).all()
    }
    trip_reviews = Review.query.filter_by(user_id=g.user.id, trip_id=trip.id).all()
    reviews_by_place = {review.place_id: review for review in trip_reviews}
    reviewed_place_ids = set(reviews_by_place)

    symbol = currency_symbol(currency)
    estimated_local = trip.estimated_trip_cost or 0

    return render_template(
        "trips/detail.html",
        trip=trip,
        currency=currency,
        money_symbol=symbol,
        total_cost_label=format_money(total_cost_usd, currency),
        estimated_cost_label=f"{symbol}{estimated_local:,.0f}",
        total_time=total_time,
        format_minutes=format_minutes,
        format_duration=format_duration,
        format_money=format_money,
        favourite_place_ids=favourite_place_ids,
        reviewed_place_ids=reviewed_place_ids,
        reviews_by_place=reviews_by_place,
        maps_directions_url=google_maps_directions_url(trip.itinerary_stops),
    )


@trips_bp.route("/<int:trip_id>/map-data")
@login_required
def map_data(trip_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=g.user.id).first_or_404()
    stops = trip.itinerary_stops
    points = [
        {
            "id": stop.place.place_id,
            "name": stop.place.name,
            "lat": stop.place.latitude,
            "lng": stop.place.longitude,
            "order": stop.visit_order,
        }
        for stop in stops
    ]

    graph_places = [place_from_mapping(place_to_algorithm_row(stop.place)) for stop in stops]
    graph = build_place_graph(graph_places)
    shortest = None
    mst = None
    all_pairs = None
    alternatives = []
    if len(graph_places) >= 2:
        start = graph_places[0].place_id
        end = graph_places[-1].place_id
        cost, path = dijkstra(graph, start, end)
        place_lookup = {place.place_id: place for place in graph_places}

        def heuristic(source_id, target_id):
            return estimate_travel_minutes(haversine_km(place_lookup[source_id], place_lookup[target_id]))

        astar_cost, astar_path = astar(graph, start, end, heuristic)
        shortest = {
            "dijkstra_minutes": round(cost, 1),
            "dijkstra_path": path,
            "astar_minutes": round(astar_cost, 1),
            "astar_path": astar_path,
        }
        mst_minutes, mst_edges = prim_mst(graph, start)
        mst = {
            "minutes": round(mst_minutes, 1),
            "edges": [
                {
                    "source": source_id,
                    "target": target_id,
                    "minutes": round(minutes, 1),
                }
                for source_id, target_id, minutes in mst_edges
            ],
        }
        distances = floyd_warshall(graph)
        all_pairs = {
            "average_minutes": round(average_shortest_path_minutes(distances), 1),
            "pairs_checked": len(graph_places) * (len(graph_places) - 1),
        }

    if graph_places:
        blocked_ids = {place.place_id for place in graph_places}
        candidate_places = [
            place_from_mapping(place_to_algorithm_row(place))
            for place in Place.query.filter_by(city=trip.city, mood_tag=trip.mood).all()
            if place.place_id not in blocked_ids
        ]
        tree = build_kdtree(candidate_places)
        alternatives = [
            {
                "name": place.name,
                "distance_km": round(distance, 2),
                "score": place.mood_match_score,
            }
            for distance, place in nearest_places(tree, graph_places[0], limit=3, blocked_ids=blocked_ids)
        ]

    return jsonify(
        {
            "points": points,
            "shortest_path": shortest,
            "mst": mst,
            "all_pairs": all_pairs,
            "alternatives": alternatives,
            "directions_url": google_maps_directions_url(stops),
        }
    )


@trips_bp.route("/<int:trip_id>/complete", methods=["POST"])
@login_required
def complete(trip_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=g.user.id).first_or_404()
    trip.status = "completed"
    db.session.commit()
    flash("Trip marked complete. You can now rate places from this itinerary.", "success")
    return redirect(url_for("trips.detail", trip_id=trip.id))


@trips_bp.route("/<int:trip_id>/favourite/<int:place_id>", methods=["POST"])
@login_required
def toggle_favourite(trip_id, place_id):
    Trip.query.filter_by(id=trip_id, user_id=g.user.id).first_or_404()
    favourite = Favourite.query.filter_by(user_id=g.user.id, place_id=place_id).first()
    if favourite:
        db.session.delete(favourite)
        flash("Removed from favourites.", "info")
    else:
        place = Place.query.get_or_404(place_id)
        db.session.add(Favourite(user_id=g.user.id, place_id=place_id))
        flash("Added to favourites.", "success")
    db.session.commit()
    return redirect(url_for("trips.detail", trip_id=trip_id))


@trips_bp.route("/<int:trip_id>/review/<int:place_id>", methods=["POST"])
@login_required
def add_review(trip_id, place_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=g.user.id).first_or_404()
    if trip.status != "completed":
        flash("Mark the trip complete before adding ratings.", "warning")
        return redirect(url_for("trips.detail", trip_id=trip.id))

    rating = int(request.form.get("rating", "5"))
    rating = max(1, min(5, rating))
    comment = request.form.get("comment", "").strip()

    review = Review.query.filter_by(user_id=g.user.id, trip_id=trip.id, place_id=place_id).first()
    if review is None:
        review = Review(user_id=g.user.id, trip_id=trip.id, place_id=place_id)
        db.session.add(review)
    review.rating = rating
    review.comment = comment
    db.session.commit()
    flash("Rating saved.", "success")
    return redirect(url_for("trips.detail", trip_id=trip.id))


@trips_bp.route("/<int:trip_id>/simulate", methods=["POST"])
@login_required
def simulate_issue(trip_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=g.user.id).first_or_404()
    unavailable_place_id = int(request.form["place_id"])
    unavailable_stop = next(
        (stop for stop in trip.itinerary_stops if stop.place_id == unavailable_place_id),
        None,
    )
    if unavailable_stop is None:
        flash("That place is not part of this itinerary.", "warning")
        return redirect(url_for("trips.detail", trip_id=trip.id))

    existing_place_ids = {stop.place.place_id for stop in trip.itinerary_stops}
    unavailable_ids = {unavailable_stop.place.place_id}
    current_cost_without_issue = sum(
        stop.place.avg_cost for stop in trip.itinerary_stops if stop.place_id != unavailable_place_id
    )
    current_time_without_issue = sum(
        stop.place.avg_time_spent_mins for stop in trip.itinerary_stops if stop.place_id != unavailable_place_id
    )
    remaining_budget = max(0, int(to_usd(trip.budget_amount, normalize_currency(getattr(trip, "currency", None) or "USD")) - current_cost_without_issue))
    remaining_time = max(0, trip.num_days * 8 * 60 - current_time_without_issue)

    candidates = [
        place_from_mapping(place_to_algorithm_row(place))
        for place in Place.query.filter_by(city=trip.city, mood_tag=trip.mood).all()
        if place.place_id not in existing_place_ids
    ]
    replacement = pick_replacement(candidates, unavailable_ids, remaining_budget, remaining_time)
    if replacement is None:
        flash("No replacement fit the remaining budget and time.", "warning")
        return redirect(url_for("trips.detail", trip_id=trip.id))

    places = [
        place_to_algorithm_row(stop.place)
        for stop in trip.itinerary_stops
        if stop.place_id != unavailable_place_id
    ]
    replacement_place = Place.query.filter_by(place_id=replacement.place_id).first()
    places.append(place_to_algorithm_row(replacement_place))
    scheduled_visits = generate_itinerary(
        places,
        city=trip.city,
        mood=trip.mood,
        budget=int(to_usd(trip.budget_amount, normalize_currency(getattr(trip, "currency", None) or "USD"))),
        days=trip.num_days,
    )
    replace_trip_stops(trip, scheduled_visits)
    db.session.commit()
    flash(f"{unavailable_stop.place.name} was unavailable, so {replacement.name} was added.", "success")
    return redirect(url_for("trips.detail", trip_id=trip.id))
