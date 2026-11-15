from datetime import date
from io import BytesIO
from urllib.parse import quote_plus

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, send_file, url_for

from algorithms.itinerary import generate_itinerary
from algorithms.kdtree import build_kdtree, nearest_places
from algorithms.crowd import crowd_aware_order
from algorithms.knapsack import place_from_mapping
from algorithms.replanner import pick_replacement
from algorithms.scheduler import format_duration, format_minutes, schedule_visits
from app.auth.routes import login_required
from app.extensions import db
from app.models import Favourite, ItineraryStop, Place, Review, Trip
from app.services.currency import (
    budget_defaults_for,
    currency_for_country,
    currency_label,
    currency_symbol,
    format_money,
    from_usd,
    normalize_currency,
    SUPPORTED_CURRENCIES,
    to_usd,
)
from app.services.ml_models import train_category_model
from app.services.place_catalog import trusted_city_places
from app.services.itinerary_pdf import build_itinerary_pdf
from app.services.trip_budget import calculate_local_trip_budget

trips_bp = Blueprint("trips", __name__)

BUDGET_DEFAULTS = {
    "Low": 100,
    "Medium": 250,
    "High": 500,
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


def google_maps_directions_url(stops, trip=None):
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
    if trip and trip.start_latitude is not None and trip.start_longitude is not None:
        origin = f"{trip.start_latitude},{trip.start_longitude}"
    destination = points[-1]
    waypoints = "|".join(points[1:-1])
    url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin}&destination={destination}&travelmode=driving"
    )
    if waypoints:
        url += f"&waypoints={waypoints}"
    return url


def google_maps_transit_url(stops, trip=None):
    """Open the itinerary in Google Maps using live public transport data."""
    if not stops:
        return ""
    points = [f"{stop.place.latitude},{stop.place.longitude}" for stop in stops if stop.place]
    if not points:
        return ""
    origin = points[0]
    if trip and trip.start_latitude is not None and trip.start_longitude is not None:
        origin = f"{trip.start_latitude},{trip.start_longitude}"
    url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin}&destination={points[-1]}&travelmode=transit"
    )
    if len(points) > 2:
        url += f"&waypoints={'|'.join(points[1:-1])}"
    return url


def city_center_coordinate(places):
    """Use the mean coordinate as a data-only city-centre fallback."""
    if not places:
        return None
    return (
        sum(place.latitude for place in places) / len(places),
        sum(place.longitude for place in places) / len(places),
    )


def travel_search_links(trip):
    """Provider search links keep live-price lookup outside our local dataset.

    Price comparison sites change inventory continuously. Linking a filled-in
    search lets the traveller verify current prices instead of presenting an
    invented 'best' fare as live data.
    """
    destination = quote_plus(trip.city)
    origin = quote_plus(trip.origin_city or "")
    travel_date = trip.travel_date or date.today().isoformat()
    return {
        "flights": f"https://www.google.com/travel/flights?q=Flights%20from%20{origin}%20to%20{destination}%20on%20{travel_date}",
        "hotels": f"https://www.google.com/travel/search?q=Hotels%20in%20{destination}%20from%20{travel_date}",
    }



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
    city_currencies = {
        city: currency_for_country(country)
        for city, country in db.session.query(Place.city, Place.country).distinct().all()
    }

    def render_setup(**extra):
        return render_template(
            "trips/setup.html",
            cities=cities,
            moods=moods,
            budget_levels=budget_levels,
            budget_defaults=BUDGET_DEFAULTS,
            budget_defaults_inr=budget_defaults_for("INR"),
            budget_defaults_by_currency={code: budget_defaults_for(code) for code in SUPPORTED_CURRENCIES},
            currency_options=[(code, currency_label(code)) for code in SUPPORTED_CURRENCIES],
            currency_symbols={code: currency_symbol(code) for code in SUPPORTED_CURRENCIES},
            city_currencies=city_currencies,
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
        origin_city = request.form.get("origin_city", "").strip()
        travel_date = request.form.get("travel_date", "").strip()
        start_location = request.form.get("start_location", "").strip()
        start_latitude_raw = request.form.get("start_latitude", "").strip()
        start_longitude_raw = request.form.get("start_longitude", "").strip()

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

        try:
            start_coordinate = (float(start_latitude_raw), float(start_longitude_raw))
        except ValueError:
            start_coordinate = None

        if not city or not mood or not budget_level or num_days < 1 or num_people < 1 or budget_amount_local <= 0:
            flash("Choose a city, mood, budget, currency, and at least one day.", "danger")
            return render_setup(currency=currency)

        matching_places = (
            Place.query.filter_by(city=city, mood_tag=mood)
            .filter(Place.category != "Hotel")
            .all()
        )
        matching_places = trusted_city_places(matching_places)
        if budget_level:
            budget_matches = [place for place in matching_places if place.budget_level == budget_level]
            if budget_matches:
                matching_places = budget_matches

        # When a custom point has not been geocoded by Google Maps, use a
        # deterministic coordinate from the selected city instead of ignoring
        # the start-point part of the route algorithm.
        if start_coordinate is None:
            start_coordinate = city_center_coordinate(matching_places)
        if not start_location:
            start_location = "City centre"

        scheduled_visits = generate_itinerary(
            [place_to_algorithm_row(place) for place in matching_places],
            city=city,
            mood=mood,
            budget=int(budget_amount_usd),
            days=num_days,
            start_coordinate=start_coordinate,
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
        hotel_options = trusted_city_places(
            Place.query.filter_by(city=city, category="Hotel").all()
        )
        attraction_cost = sum(visit.place.avg_cost for visit in scheduled_visits)
        local_budget = calculate_local_trip_budget(
            budget_level=budget_level,
            num_days=num_days,
            num_people=num_people,
            attraction_cost=attraction_cost,
            hotels=hotel_options,
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
            origin_city=origin_city or None,
            travel_date=travel_date or None,
            start_location=start_location,
            start_latitude=start_coordinate[0] if start_coordinate else None,
            start_longitude=start_coordinate[1] if start_coordinate else None,
            predicted_category=category_prediction,
            estimated_trip_cost=round(from_usd(local_budget["total"], currency), 2),
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

    hotel_options = trusted_city_places(
        Place.query.filter_by(city=trip.city, category="Hotel")
        .order_by(Place.avg_rating.desc(), Place.avg_cost.asc())
        .all()
    )[:10]
    local_budget = calculate_local_trip_budget(
        budget_level=trip.budget_level,
        num_days=trip.num_days,
        num_people=trip.num_people,
        attraction_cost=total_cost_usd,
        hotels=hotel_options,
    )
    budget_amount_usd = to_usd(trip.budget_amount, currency)
    local_budget["difference"] = round(budget_amount_usd - local_budget["total"], 2)
    local_budget["over_budget"] = local_budget["difference"] < 0

    return render_template(
        "trips/detail.html",
        trip=trip,
        currency=currency,
        total_cost_label=format_money(total_cost_usd, currency),
        local_budget=local_budget,
        total_time=total_time,
        format_minutes=format_minutes,
        format_duration=format_duration,
        format_money=format_money,
        favourite_place_ids=favourite_place_ids,
        reviewed_place_ids=reviewed_place_ids,
        reviews_by_place=reviews_by_place,
        maps_directions_url=google_maps_directions_url(trip.itinerary_stops, trip),
        maps_transit_url=google_maps_transit_url(trip.itinerary_stops, trip),
        travel_links=travel_search_links(trip),
        hotel_options=hotel_options,
    )


@trips_bp.route("/<int:trip_id>/download")
@login_required
def download_itinerary(trip_id):
    """Download the saved itinerary as a printable PDF."""
    trip = Trip.query.filter_by(id=trip_id, user_id=g.user.id).first_or_404()
    currency = normalize_currency(trip.currency or "USD")
    attraction_cost = sum(stop.place.avg_cost for stop in trip.itinerary_stops)
    hotels = trusted_city_places(Place.query.filter_by(city=trip.city, category="Hotel").all())
    local_budget = calculate_local_trip_budget(
        budget_level=trip.budget_level,
        num_days=trip.num_days,
        num_people=trip.num_people,
        attraction_cost=attraction_cost,
        hotels=hotels,
    )
    document = build_itinerary_pdf(trip, local_budget, currency)
    safe_city = "".join(character for character in trip.city if character.isalnum() or character in {"-", "_"})
    return send_file(
        BytesIO(document),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"mood-{safe_city.lower()}-itinerary.pdf",
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

    return jsonify(
        {
            "points": points,
            "city": trip.city,
            "start": (
                {
                    "name": trip.start_location or "City centre",
                    "lat": trip.start_latitude,
                    "lng": trip.start_longitude,
                }
                if trip.start_latitude is not None and trip.start_longitude is not None
                else None
            ),
            "directions_url": google_maps_directions_url(stops, trip),
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
@trips_bp.route("/<int:trip_id>/replace-stop", methods=["POST"])
@login_required
def simulate_issue(trip_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=g.user.id).first_or_404()
    unavailable_place_id = int(request.form["place_id"])
    reason = request.form.get("reason", "unavailable").strip().lower()
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

    candidate_places = trusted_city_places(
        Place.query.filter_by(city=trip.city, mood_tag=trip.mood).all()
    )
    candidates = [
        place_from_mapping(place_to_algorithm_row(place))
        for place in candidate_places
        if place.place_id not in existing_place_ids
    ]

    is_crowded = (reason == "crowded")
    crowd_levels = {p.place_id: (p.crowd_level or "Medium") for p in Place.query.filter_by(city=trip.city).all()}
    replacement = pick_replacement(
        candidates,
        unavailable_ids,
        remaining_budget,
        remaining_time,
        prefer_lower_crowd=is_crowded,
        crowd_levels=crowd_levels,
    )
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

    if is_crowded:
        flash(f"{unavailable_stop.place.name} was marked crowded; {replacement.name} was scheduled as a calmer replacement.", "success")
    else:
        flash(f"{unavailable_stop.place.name} was marked unavailable; {replacement.name} was added in its place.", "success")
    return redirect(url_for("trips.detail", trip_id=trip.id))


@trips_bp.route("/<int:trip_id>/replace-nearby", methods=["POST"])
@login_required
def replace_with_nearby(trip_id):
    """Replace one stop with a KD-Tree verified nearby mood match."""
    trip = Trip.query.filter_by(id=trip_id, user_id=g.user.id).first_or_404()
    stop_id = request.form.get("stop_id", type=int)
    replacement_place_id = request.form.get("replacement_place_id", type=int)
    anchor_stop = next((stop for stop in trip.itinerary_stops if stop.id == stop_id), None)
    replacement = Place.query.get_or_404(replacement_place_id)
    if anchor_stop is None:
        flash("Choose a stop from this itinerary first.", "warning")
        return redirect(url_for("tools.nearby", trip_id=trip.id))

    existing_ids = {stop.place_id for stop in trip.itinerary_stops}
    catalog = trusted_city_places(
        Place.query.filter_by(city=trip.city, mood_tag=trip.mood).filter(Place.category != "Hotel").all()
    )
    candidate_rows = [place for place in catalog if place.id not in existing_ids]
    if replacement not in candidate_rows:
        flash("That nearby place is not available for this trip.", "warning")
        return redirect(url_for("tools.nearby", trip_id=trip.id, stop_id=anchor_stop.id))

    anchor = place_from_mapping(place_to_algorithm_row(anchor_stop.place))
    tree = build_kdtree([place_from_mapping(place_to_algorithm_row(place)) for place in candidate_rows])
    nearby_ids = {candidate.place_id for _, candidate in nearest_places(tree, anchor, limit=8)}
    if replacement.place_id not in nearby_ids:
        flash("Choose one of the suggested nearby places.", "warning")
        return redirect(url_for("tools.nearby", trip_id=trip.id, stop_id=anchor_stop.id))

    other_stops = [stop for stop in trip.itinerary_stops if stop.id != anchor_stop.id]
    currency = normalize_currency(trip.currency or "USD")
    attraction_cost = sum(stop.place.avg_cost for stop in other_stops) + replacement.avg_cost
    total_time = sum(stop.place.avg_time_spent_mins for stop in other_stops) + replacement.avg_time_spent_mins
    if attraction_cost > to_usd(trip.budget_amount, currency) or total_time > trip.num_days * 8 * 60:
        flash("That nearby place does not fit this trip's remaining time or attraction budget.", "warning")
        return redirect(url_for("tools.nearby", trip_id=trip.id, stop_id=anchor_stop.id))

    ordered = [place_from_mapping(place_to_algorithm_row(stop.place)) for stop in trip.itinerary_stops]
    anchor_index = next(index for index, stop in enumerate(trip.itinerary_stops) if stop.id == anchor_stop.id)
    ordered[anchor_index] = place_from_mapping(place_to_algorithm_row(replacement))
    scheduled = schedule_visits(ordered, days=trip.num_days)
    if len(scheduled) != len(ordered) or replacement.place_id not in {visit.place.place_id for visit in scheduled}:
        flash("That nearby place cannot be scheduled during its opening hours.", "warning")
        return redirect(url_for("tools.nearby", trip_id=trip.id, stop_id=anchor_stop.id))

    replace_trip_stops(trip, scheduled)
    db.session.commit()
    flash(f"{anchor_stop.place.name} was replaced with nearby {replacement.name}.", "success")
    return redirect(url_for("trips.detail", trip_id=trip.id))


@trips_bp.route("/<int:trip_id>/crowd-optimize", methods=["POST"])
@login_required
def crowd_optimize(trip_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=g.user.id).first_or_404()
    places = [place_from_mapping(place_to_algorithm_row(stop.place)) for stop in trip.itinerary_stops]
    if len(places) < 2:
        flash("Add at least two stops before optimising for crowds.", "warning")
        return redirect(url_for("trips.detail", trip_id=trip.id))

    crowd_levels = {stop.place.place_id: stop.place.crowd_level or "Medium" for stop in trip.itinerary_stops}
    ordered = crowd_aware_order(places, crowd_levels)
    from algorithms.scheduler import schedule_visits

    replace_trip_stops(trip, schedule_visits(ordered, days=trip.num_days))
    db.session.commit()
    flash("Route timing updated: high-crowd stops were prioritised for earlier visits.", "success")
    return redirect(url_for("trips.detail", trip_id=trip.id))


