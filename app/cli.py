import csv

import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import Place
from app.services.search import reset_place_trie


@click.command("init-db")
@with_appcontext
def init_db():
    """Create all SQLite tables for the project."""
    db.create_all()
    click.echo("Database tables created.")


@click.command("reset-db")
@with_appcontext
def reset_db():
    """Drop and recreate all SQLite tables. Use during development only."""
    db.drop_all()
    db.create_all()
    reset_place_trie()
    click.echo("Database reset.")


def parse_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


@click.command("import-places")
@click.argument("csv_path", default="data/places.csv", required=False)
@with_appcontext
def import_places(csv_path):
    """Import places.csv into the Place table."""
    created = 0
    updated = 0

    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            place = Place.query.filter_by(place_id=row["place_id"]).first()
            if place is None:
                place = Place(place_id=row["place_id"])
                created += 1
            else:
                updated += 1

            place.name = row["name"]
            place.city = row["city"]
            place.country = row["country"]
            place.continent = row["continent"]
            place.category = row["category"]
            place.mood_tag = row["mood_tag"]
            place.latitude = parse_float(row["latitude"])
            place.longitude = parse_float(row["longitude"])
            place.avg_cost = parse_float(row["avg_cost"])
            place.avg_time_spent_mins = parse_int(row["avg_time_spent_mins"], 60)
            place.opening_time = row.get("opening_time")
            place.closing_time = row.get("closing_time")
            place.opening_minutes = parse_int(row.get("opening_minutes"), 0)
            place.closing_minutes = parse_int(row.get("closing_minutes"), 1440)
            place.avg_rating = parse_float(row.get("avg_rating"))
            place.mood_match_score = parse_float(row.get("mood_match_score"))
            place.annual_visitors_millions = parse_float(row.get("annual_visitors_millions"))
            place.unesco_site = parse_bool(row.get("unesco_site"))
            place.best_season = row.get("best_season")
            place.currency = row.get("currency")
            place.budget_level = row.get("budget_level")
            place.distance_from_city_center_km = parse_float(row.get("distance_from_city_center_km"))
            place.crowd_level = row.get("crowd_level")
            place.indoor_outdoor = row.get("indoor_outdoor")
            place.family_friendly = parse_bool(row.get("family_friendly"))
            place.popularity_score = parse_float(row.get("popularity_score"))
            db.session.add(place)

    db.session.commit()
    reset_place_trie()
    click.echo(f"Imported places: {created} created, {updated} updated.")
