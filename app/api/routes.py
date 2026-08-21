from flask import Blueprint, jsonify, request

from app.auth.routes import login_required
from app.services.plan_preview import build_plan_preview
from app.services.search import search_places
from app.models import Place

api_bp = Blueprint("api", __name__)


@api_bp.route("/search")
@login_required
def search_places_route():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([])

    place_ids = search_places(query)
    places = Place.query.filter(Place.id.in_(place_ids)).all()
    places_by_id = {place.id: place for place in places}
    ordered_places = [places_by_id[place_id] for place_id in place_ids if place_id in places_by_id]

    return jsonify(
        [
            {
                "id": place.id,
                "name": place.name,
                "city": place.city,
                "category": place.category,
                "rating": place.avg_rating,
                "setup_url": f"/trips/setup?city={place.city}",
            }
            for place in ordered_places
        ]
    )


@api_bp.route("/plan-insights", methods=["POST"])
@login_required
def plan_insights():
    payload = request.get_json(force=True)
    required = ("city", "mood_preference", "budget_level", "budget_amount", "num_days", "num_people")
    missing = [field for field in required if not payload.get(field)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        payload["budget_amount"] = float(payload["budget_amount"])
        payload["num_days"] = int(payload["num_days"])
        payload["num_people"] = int(payload["num_people"])
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid number in budget, days, or people."}), 400

    if payload["budget_amount"] <= 0 or payload["num_days"] < 1 or payload["num_people"] < 1:
        return jsonify({"error": "Budget, days, and people must be positive."}), 400

    return jsonify(build_plan_preview(payload))
