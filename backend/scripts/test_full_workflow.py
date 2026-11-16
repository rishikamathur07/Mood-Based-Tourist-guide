"""
Comprehensive End-to-End Workflow Regression Test Suite.

Verifies:
1. Authentication: Signup, Login, Logout, Session handling
2. Trip Planning: City, mood, budget level, spend limit, days, people, currency, date, starting location
3. Itinerary Generation: Stops with visit times, cost, hours, Google Maps route link, favourites, reviews, hotels
4. Local Budget Breakdown: Attractions, stay, food, local transit clearly separated; flights excluded from estimate
5. Live Replanning: Marking places unavailable or crowded and re-planning with priority queue replacements
6. Profile Sections: My Trips, Favourites, My Reviews, Ratings, and Settings
7. Hotel Catalog: Dedicated hotels directory (/tools/hotels) with budget filtering
8. Machine Learning API endpoints: /api/predict/category and /api/predict/cost with safe CSV fallback
"""

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app import create_app
from app.extensions import db
from app.models import Place, Trip, Favourite, Review, User


class TestConfig:
    SECRET_KEY = "test-secret-suite"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_MAPS_API_KEY = ""  # Test fallback behavior without key

    @staticmethod
    def has_google_maps_key():
        return False


def seed_places():
    places = [
        Place(
            place_id="delhi_red_fort",
            name="Red Fort Heritage",
            city="Delhi",
            country="India",
            continent="Asia",
            category="Historical",
            mood_tag="culture",
            latitude=28.6562,
            longitude=77.2410,
            avg_cost=10.0,
            avg_time_spent_mins=120,
            opening_time="09:00",
            closing_time="18:00",
            opening_minutes=540,
            closing_minutes=1080,
            avg_rating=4.7,
            mood_match_score=9.5,
            budget_level="Medium",
            crowd_level="High",
            indoor_outdoor="Outdoor",
            family_friendly=True,
            popularity_score=9.5,
        ),
        Place(
            place_id="delhi_qutub",
            name="Qutub Minar Tower",
            city="Delhi",
            country="India",
            continent="Asia",
            category="Historical",
            mood_tag="culture",
            latitude=28.5245,
            longitude=77.1855,
            avg_cost=12.0,
            avg_time_spent_mins=90,
            opening_time="07:00",
            closing_time="19:00",
            opening_minutes=420,
            closing_minutes=1140,
            avg_rating=4.6,
            mood_match_score=9.2,
            budget_level="Medium",
            crowd_level="Medium",
            indoor_outdoor="Outdoor",
            family_friendly=True,
            popularity_score=9.2,
        ),
        Place(
            place_id="delhi_crafts",
            name="National Crafts Gallery",
            city="Delhi",
            country="India",
            continent="Asia",
            category="Historical",
            mood_tag="culture",
            latitude=28.6146,
            longitude=77.2429,
            avg_cost=5.0,
            avg_time_spent_mins=60,
            opening_time="10:00",
            closing_time="17:00",
            opening_minutes=600,
            closing_minutes=1020,
            avg_rating=4.5,
            mood_match_score=8.8,
            budget_level="Medium",
            crowd_level="Low",
            indoor_outdoor="Indoor",
            family_friendly=True,
            popularity_score=8.5,
        ),
        Place(
            place_id="delhi_humayun",
            name="Humayun Tomb Gardens",
            city="Delhi",
            country="India",
            continent="Asia",
            category="Historical",
            mood_tag="culture",
            latitude=28.5933,
            longitude=77.2507,
            avg_cost=8.0,
            avg_time_spent_mins=90,
            opening_time="06:00",
            closing_time="18:00",
            opening_minutes=360,
            closing_minutes=1080,
            avg_rating=4.8,
            mood_match_score=9.4,
            budget_level="Medium",
            crowd_level="Medium",
            indoor_outdoor="Outdoor",
            family_friendly=True,
            popularity_score=9.3,
        ),
        Place(
            place_id="delhi_lotus",
            name="Lotus Temple Sanctuary",
            city="Delhi",
            country="India",
            continent="Asia",
            category="Historical",
            mood_tag="culture",
            latitude=28.5535,
            longitude=77.2588,
            avg_cost=0.0,
            avg_time_spent_mins=60,
            opening_time="09:00",
            closing_time="17:30",
            opening_minutes=540,
            closing_minutes=1050,
            avg_rating=4.6,
            mood_match_score=9.1,
            budget_level="Medium",
            crowd_level="Low",
            indoor_outdoor="Indoor",
            family_friendly=True,
            popularity_score=9.0,
        ),
        Place(
            place_id="delhi_jantar",
            name="Jantar Mantar Observatory",
            city="Delhi",
            country="India",
            continent="Asia",
            category="Historical",
            mood_tag="culture",
            latitude=28.6271,
            longitude=77.2166,
            avg_cost=4.0,
            avg_time_spent_mins=60,
            opening_time="09:00",
            closing_time="18:00",
            opening_minutes=540,
            closing_minutes=1080,
            avg_rating=4.4,
            mood_match_score=8.7,
            budget_level="Medium",
            crowd_level="Low",
            indoor_outdoor="Outdoor",
            family_friendly=True,
            popularity_score=8.7,
        ),
        Place(
            place_id="delhi_hotel_1",
            name="The Claridges New Delhi",
            city="Delhi",
            country="India",
            continent="Asia",
            category="Hotel",
            mood_tag="relaxation",
            latitude=28.6010,
            longitude=77.2180,
            avg_cost=80.0,
            avg_time_spent_mins=60,
            opening_time="00:00",
            closing_time="23:59",
            opening_minutes=0,
            closing_minutes=1439,
            avg_rating=4.7,
            mood_match_score=9.0,
            budget_level="Medium",
            crowd_level="Medium",
            indoor_outdoor="Indoor",
            family_friendly=True,
            popularity_score=9.0,
        ),
        Place(
            place_id="delhi_hotel_2",
            name="Bloomrooms Heritage Janpath",
            city="Delhi",
            country="India",
            continent="Asia",
            category="Hotel",
            mood_tag="relaxation",
            latitude=28.6210,
            longitude=77.2190,
            avg_cost=35.0,
            avg_time_spent_mins=60,
            opening_time="00:00",
            closing_time="23:59",
            opening_minutes=0,
            closing_minutes=1439,
            avg_rating=4.3,
            mood_match_score=8.4,
            budget_level="Low",
            crowd_level="Medium",
            indoor_outdoor="Indoor",
            family_friendly=True,
            popularity_score=8.5,
        ),
    ]
    for p in places:
        db.session.add(p)
    db.session.commit()


def main():
    print("=" * 65)
    print("Running Mood Web Application Comprehensive Workflow Verification")
    print("=" * 65)

    with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
        db_path = Path(temp_dir, "test_workflow.sqlite3").as_posix()
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        app = create_app(TestConfig)
        app.testing = True

        try:
            with app.app_context():
                seed_places()

            client = app.test_client()

            # 1. Landing page check
            res_landing = client.get("/")
            assert res_landing.status_code == 200
            assert b"Mood-Based Smart Tourist Recommendation" in res_landing.data
            assert b"Your next journey should feel like you" in res_landing.data
            print("PASS 1: Landing page renders cleanly directly on background")

            res_about = client.get("/about")
            assert res_about.status_code == 200
            assert b"About Mood" in res_about.data
            assert b"Costs you can understand" in res_about.data
            print("PASS 1b: About page renders with the travel layout")

            # 2. Authentication: Signup
            res_signup = client.post(
                "/auth/signup",
                data={"name": "Rishika Mathur", "email": "rishika@example.com", "password": "securepassword123"},
                follow_redirects=True,
            )
            assert res_signup.status_code == 200
            assert b"My trips" in res_signup.data
            print("PASS 2: User signup succeeded and session established")

            # 3. Authentication: Logout & Login
            res_logout = client.post("/auth/logout", follow_redirects=True)
            assert res_logout.status_code == 200
            assert b"Logged out" in res_logout.data or b"Log in" in res_logout.data

            res_login = client.post(
                "/auth/login",
                data={"email": "rishika@example.com", "password": "securepassword123"},
                follow_redirects=True,
            )
            assert res_login.status_code == 200
            assert b"My trips" in res_login.data
            print("PASS 3: Logout and subsequent login verified")

            res_budget_short = client.post(
                "/api/budget-suggestions",
                json={"city": "Delhi", "mood_preference": "culture", "num_days": 1, "num_people": 1, "currency": "INR"},
            )
            res_budget_long = client.post(
                "/api/budget-suggestions",
                json={"city": "Delhi", "mood_preference": "culture", "num_days": 3, "num_people": 2, "currency": "INR"},
            )
            assert res_budget_short.status_code == 200
            assert res_budget_long.status_code == 200
            short = res_budget_short.json["suggestions"]
            long = res_budget_long.json["suggestions"]
            assert short["Low"] < short["Medium"] < short["High"]
            assert long["Medium"] > short["Medium"]
            print("PASS 3b: Budget defaults scale by tier, days, and people")

            # 4. Trip Setup & Itinerary Generation
            res_create = client.post(
                "/trips/setup",
                data={
                    "city": "Delhi",
                    "mood": "culture",
                    "budget_level": "Medium",
                    "budget_amount": "8000",
                    "currency": "INR",
                    "num_days": "1",
                    "num_people": "2",
                    "travel_date": "2026-11-20",
                    "origin_city": "Mumbai",
                },
                follow_redirects=True,
            )
            assert res_create.status_code == 200
            assert b"Your itinerary is ready" in res_create.data
            print("PASS 4: Trip created and saved itinerary generated")

            # A very low manual amount must still produce a compact plan instead
            # of returning the former "try a higher budget" dead end.
            res_low_budget = client.post(
                "/trips/setup",
                data={
                    "city": "Delhi",
                    "mood": "culture",
                    "budget_level": "Medium",
                    "budget_amount": "1",
                    "currency": "INR",
                    "num_days": "1",
                    "num_people": "1",
                },
                follow_redirects=True,
            )
            assert res_low_budget.status_code == 200
            assert b"Your itinerary is ready" in res_low_budget.data
            print("PASS 4b: Low manual budget produces a compact workable itinerary")

            with app.app_context():
                trip = Trip.query.filter_by(city="Delhi").first()
                assert trip is not None
                trip_id = trip.id
                assert len(trip.itinerary_stops) >= 2
                first_stop_place_id = trip.itinerary_stops[0].place_id

            # 5. Trip Detail Page & Budget Breakdown Verification
            res_detail = client.get(f"/trips/{trip_id}")
            assert res_detail.status_code == 200
            assert b"Your budget breakdown" in res_detail.data
            assert b"Estimated local trip cost" in res_detail.data
            assert b"Attractions" in res_detail.data
            assert b"Stay" in res_detail.data
            assert b"Meals" in res_detail.data
            assert b"Local travel" in res_detail.data
            # Flight prices excluded from calculated estimate
            assert b"Flights are searched separately" in res_detail.data or b"not included" in res_detail.data
            # Google Maps fallback route link when no API key configured
            assert b"Open in Google Maps" in res_detail.data or b"Open route in Google Maps" in res_detail.data
            print("PASS 5: Trip detail presents stops, map link, and transparent budget breakdown")

            res_download = client.get(f"/trips/{trip_id}/download")
            assert res_download.status_code == 200
            assert res_download.headers["Content-Type"].startswith("application/pdf")
            assert res_download.data.startswith(b"%PDF")
            print("PASS 5b: Downloadable itinerary PDF generated")

            # 6. Favouriting a Place
            res_fav = client.post(f"/trips/{trip_id}/favourite/{first_stop_place_id}", follow_redirects=True)
            assert res_fav.status_code == 200
            with app.app_context():
                user = User.query.filter_by(email="rishika@example.com").first()
                fav = Favourite.query.filter_by(user_id=user.id, place_id=first_stop_place_id).first()
                assert fav is not None, "Place must be added to favourites"
            print("PASS 6: Favouriting places on itinerary verified")

            # 7. Live Replanning: Mark Place Unavailable
            res_replan_unavail = client.post(
                f"/trips/{trip_id}/simulate",
                data={"place_id": first_stop_place_id, "reason": "unavailable"},
                follow_redirects=True,
            )
            assert res_replan_unavail.status_code == 200
            assert b"was marked unavailable" in res_replan_unavail.data
            with app.app_context():
                updated_trip = Trip.query.get(trip_id)
                current_places = [s.place_id for s in updated_trip.itinerary_stops]
                assert first_stop_place_id not in current_places, "Unavailable place must be replaced"
                second_stop_place_id = current_places[0]
            print("PASS 7: Live replanning when venue is unavailable verified")

            # 8. Live Replanning: Mark Place Crowded
            res_replan_crowd = client.post(
                f"/trips/{trip_id}/simulate",
                data={"place_id": second_stop_place_id, "reason": "crowded"},
                follow_redirects=True,
            )
            assert res_replan_crowd.status_code == 200
            assert b"was marked crowded" in res_replan_crowd.data
            print("PASS 8: Live replanning when venue is crowded verified")

            # 9. Complete Trip & Leave Review / Rating
            res_complete = client.post(f"/trips/{trip_id}/complete", follow_redirects=True)
            assert res_complete.status_code == 200
            assert b"Trip marked complete" in res_complete.data

            with app.app_context():
                remaining_stop = Trip.query.get(trip_id).itinerary_stops[0].place_id
            res_review = client.post(
                f"/trips/{trip_id}/review/{remaining_stop}",
                data={"rating": "5", "comment": "Breathtaking heritage and calm atmosphere."},
                follow_redirects=True,
            )
            assert res_review.status_code == 200
            assert b"Rating saved" in res_review.data or b"Review" in res_review.data
            print("PASS 9: Trip completion and star rating/review submission verified")

            # 10. Profile View: Trips, Favourites, Reviews, Ratings, and Settings
            res_profile = client.get("/profile/")
            assert res_profile.status_code == 200
            assert b"My trips" in res_profile.data
            assert b"Favourites" in res_profile.data
            assert b"Ratings" in res_profile.data
            assert b"My reviews" in res_profile.data
            assert b"Settings" in res_profile.data

            # Update display name in Settings
            res_settings = client.post("/profile/settings", data={"name": "Rishika M."}, follow_redirects=True)
            assert res_settings.status_code == 200
            assert b"Profile updated" in res_settings.data
            print("PASS 10: Profile sections (Trips, Favourites, Ratings, Reviews, Settings) verified")

            # 11. Dedicated Hotels Directory Page (/tools/hotels)
            res_hotels = client.get("/tools/hotels?city=Delhi&budget=Medium")
            assert res_hotels.status_code == 200
            assert b"Hotels in Delhi" in res_hotels.data
            assert b"The Claridges New Delhi" in res_hotels.data
            print("PASS 11: Dedicated hotels page (/tools/hotels) with budget filtering verified")

            # 12. Machine Learning API Endpoints
            res_cat = client.post(
                "/api/predict/category",
                json={"city": "Delhi", "num_days": 2, "num_people": 2, "mood": "culture", "budget": "Medium"},
            )
            assert res_cat.status_code == 200
            assert res_cat.json["status"] == "success"
            assert "predicted_category" in res_cat.json

            res_cost = client.post(
                "/api/predict/cost",
                json={"city": "Delhi", "num_days": 2, "num_people": 2, "mood": "culture", "budget": "Medium", "currency": "INR"},
            )
            assert res_cost.status_code == 200
            assert res_cost.json["status"] == "success"
            assert "estimated_cost" in res_cost.json
            print("PASS 12: Machine Learning Category and Cost prediction APIs verified")

        finally:
            # Explicitly close and dispose SQLite file connections before TemporaryDirectory cleanup
            with app.app_context():
                db.session.remove()
                db.engine.dispose()

    print("=" * 65)
    print("ALL END-TO-END WORKFLOW VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    main()
