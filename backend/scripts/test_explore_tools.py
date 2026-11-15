"""Smoke test Explore tools and plan preview API."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app import create_app
from app.extensions import db
from app.models import Place, Trip, User


def main():
    app = create_app()
    client = app.test_client()

    with app.app_context():
        user = User.query.first()
        trip = Trip.query.first()
        place = Place.query.first()
        if not user or not trip or not place:
            print("FAIL: Need at least one user, trip, and place in the database.")
            print("Run: flask init-db && flask import-places, then sign up and create a trip.")
            return 1

        city = trip.city
        mood = trip.mood
        stop = trip.itinerary_stops[0] if trip.itinerary_stops else None

        with client.session_transaction() as sess:
            sess["user_id"] = user.id

        checks = [
            ("GET", "/tools/", None, 200),
            ("GET", f"/tools/discover?city={city}&mood={mood}", None, 200),
            ("GET", f"/tools/compare?left={trip.id}&right={trip.id}", None, 200),
            ("GET", f"/tools/nearby?trip_id={trip.id}", None, 200),
            ("GET", f"/tools/budget?city={city}&mood={mood}&currency=INR&amount=5000", None, 200),
            ("GET", "/tools/favourites", None, 200),
            ("GET", f"/tools/hotels?city={city}", None, 200),
            (
                "POST",
                "/api/plan-insights",
                {
                    "city": city,
                    "mood_preference": mood,
                    "budget_level": trip.budget_level,
                    "budget_amount": float(trip.budget_amount or 1000),
                    "currency": getattr(trip, "currency", None) or "INR",
                    "num_days": trip.num_days,
                    "num_people": trip.num_people,
                },
                200,
            ),
        ]

        failed = 0
        for method, path, json_body, expected in checks:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path, json=json_body)
            ok = response.status_code == expected
            status = "PASS" if ok else "FAIL"
            print(f"{status} {method} {path} -> {response.status_code}")
            if not ok:
                failed += 1
                print(response.get_data(as_text=True)[:300])

        if stop:
            response = client.get(f"/tools/nearby?trip_id={trip.id}&stop_id={stop.id}")
            ok = response.status_code == 200
            print(f"{'PASS' if ok else 'FAIL'} GET nearby with stop_id -> {response.status_code}")
            if not ok:
                failed += 1

        discover = client.get(f"/tools/discover?city={city}&mood={mood}")
        body = discover.get_data(as_text=True)
        has_places = place.name.split("(")[0].strip()[:8] in body or "place" in body.lower()
        print(f"{'PASS' if has_places else 'WARN'} discover page contains place data")

        print(f"\nDone: {failed} failed checks")
        return failed


if __name__ == "__main__":
    raise SystemExit(main())
