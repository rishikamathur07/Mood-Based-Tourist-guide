from flask import Blueprint, jsonify, request

from app.auth.routes import login_required
from app.models import Place
from app.services.currency import format_money, from_usd, normalize_currency
from app.services.ml_models import model_report, train_category_model, train_cost_model
from app.services.plan_preview import build_budget_suggestions, build_plan_preview
from app.services.search import search_places

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


@api_bp.route("/budget-suggestions", methods=["POST"])
@login_required
def budget_suggestions():
    """Suggest transparent, group-aware local-trip budgets for the setup form."""
    payload = request.get_json(force=True)
    required = ("city", "mood_preference", "num_days", "num_people")
    missing = [field for field in required if not payload.get(field)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        payload["num_days"] = int(payload["num_days"])
        payload["num_people"] = int(payload["num_people"])
    except (TypeError, ValueError):
        return jsonify({"error": "Days and people must be whole numbers."}), 400

    if payload["num_days"] < 1 or payload["num_people"] < 1:
        return jsonify({"error": "Days and people must be positive."}), 400

    return jsonify(build_budget_suggestions(payload))


@api_bp.route("/predict/category", methods=["GET", "POST"])
def predict_category():
    """Predict preferred place category using Decision Tree (or CSV fallback)."""
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
    else:
        data = request.args.to_dict()

    city = data.get("city", "Delhi").strip()
    days = int(data.get("days") or data.get("num_days") or 2)
    people = int(data.get("people") or data.get("num_people") or 2)
    mood = (data.get("mood") or data.get("mood_preference") or "culture").strip().lower()
    budget = (data.get("budget") or data.get("budget_level") or "Medium").strip().capitalize()

    prediction = train_category_model().predict(
        [
            {
                "city": city,
                "num_days": days,
                "num_people": people,
                "mood_preference": mood,
                "budget_level": budget,
            }
        ]
    )[0]

    return jsonify(
        {
            "status": "success",
            "city": city,
            "mood": mood,
            "budget_level": budget,
            "num_days": days,
            "num_people": people,
            "predicted_category": prediction,
        }
    )


@api_bp.route("/predict/cost", methods=["GET", "POST"])
def predict_cost():
    """Estimate total trip cost using Linear Regression (or CSV fallback)."""
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
    else:
        data = request.args.to_dict()

    city = data.get("city", "Delhi").strip()
    days = int(data.get("days") or data.get("num_days") or 2)
    people = int(data.get("people") or data.get("num_people") or 2)
    mood = (data.get("mood") or data.get("mood_preference") or "culture").strip().lower()
    budget = (data.get("budget") or data.get("budget_level") or "Medium").strip().capitalize()
    currency = normalize_currency(data.get("currency", "USD"))

    predicted_usd = float(
        train_cost_model().predict(
            [
                {
                    "city": city,
                    "num_days": days,
                    "num_people": people,
                    "mood_preference": mood,
                    "budget_level": budget,
                }
            ]
        )[0]
    )
    predicted_usd = max(20.0, predicted_usd)
    converted_amount = round(from_usd(predicted_usd, currency), 2)

    return jsonify(
        {
            "status": "success",
            "city": city,
            "mood": mood,
            "budget_level": budget,
            "num_days": days,
            "num_people": people,
            "currency": currency,
            "estimated_cost": converted_amount,
            "formatted_cost": format_money(predicted_usd, currency),
        }
    )


@api_bp.route("/model-report")
@login_required
def get_model_report():
    return jsonify(model_report())
