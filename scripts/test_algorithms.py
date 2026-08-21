import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from algorithms.itinerary import generate_itinerary
from algorithms.scheduler import format_minutes


sample_places = [
    {
        "place_id": "p1",
        "name": "City Museum",
        "city": "Jaipur",
        "mood_tag": "calm",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "avg_cost": 300,
        "avg_time_spent_mins": 120,
        "opening_minutes": 600,
        "closing_minutes": 1080,
        "mood_match_score": 9.0,
    },
    {
        "place_id": "p2",
        "name": "Lake Walk",
        "city": "Jaipur",
        "mood_tag": "calm",
        "latitude": 26.9417,
        "longitude": 75.7780,
        "avg_cost": 100,
        "avg_time_spent_mins": 90,
        "opening_minutes": 540,
        "closing_minutes": 1140,
        "mood_match_score": 7.5,
    },
    {
        "place_id": "p3",
        "name": "Adventure Park",
        "city": "Jaipur",
        "mood_tag": "adventure",
        "latitude": 26.8500,
        "longitude": 75.8000,
        "avg_cost": 700,
        "avg_time_spent_mins": 180,
        "opening_minutes": 600,
        "closing_minutes": 1020,
        "mood_match_score": 9.5,
    },
    {
        "place_id": "p4",
        "name": "Quiet Garden",
        "city": "Jaipur",
        "mood_tag": "calm",
        "latitude": 26.9000,
        "longitude": 75.8100,
        "avg_cost": 150,
        "avg_time_spent_mins": 75,
        "opening_minutes": 570,
        "closing_minutes": 1110,
        "mood_match_score": 8.0,
    },
]


def main():
    itinerary = generate_itinerary(sample_places, city="Jaipur", mood="calm", budget=500, days=1)

    assert itinerary, "Expected at least one scheduled visit"
    assert all(visit.place.mood_tag == "calm" for visit in itinerary)
    assert sum(visit.place.avg_cost for visit in itinerary) <= 500
    assert all(visit.start_minutes >= visit.place.opening_minutes for visit in itinerary)
    assert all(visit.end_minutes <= visit.place.closing_minutes for visit in itinerary)

    for visit in itinerary:
        print(
            f"Day {visit.day}: {visit.place.name} "
            f"{format_minutes(visit.start_minutes)}-{format_minutes(visit.end_minutes)}"
        )


if __name__ == "__main__":
    main()
