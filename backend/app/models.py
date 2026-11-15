from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    trips = db.relationship("Trip", back_populates="user", cascade="all, delete-orphan")
    reviews = db.relationship("Review", back_populates="user", cascade="all, delete-orphan")
    favourites = db.relationship("Favourite", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Place(db.Model):
    __tablename__ = "places"

    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    city = db.Column(db.String(120), nullable=False, index=True)
    country = db.Column(db.String(120), nullable=False)
    continent = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(120), nullable=False, index=True)
    mood_tag = db.Column(db.String(80), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    avg_cost = db.Column(db.Float, nullable=False, default=0)
    avg_time_spent_mins = db.Column(db.Integer, nullable=False, default=60)
    opening_time = db.Column(db.String(20), nullable=True)
    closing_time = db.Column(db.String(20), nullable=True)
    opening_minutes = db.Column(db.Integer, nullable=False, default=0)
    closing_minutes = db.Column(db.Integer, nullable=False, default=1440)
    avg_rating = db.Column(db.Float, nullable=False, default=0)
    mood_match_score = db.Column(db.Float, nullable=False, default=0)
    annual_visitors_millions = db.Column(db.Float, nullable=True)
    unesco_site = db.Column(db.Boolean, nullable=False, default=False)
    best_season = db.Column(db.String(80), nullable=True)
    currency = db.Column(db.String(10), nullable=True)
    budget_level = db.Column(db.String(40), nullable=True, index=True)
    distance_from_city_center_km = db.Column(db.Float, nullable=True)
    crowd_level = db.Column(db.String(40), nullable=True)
    indoor_outdoor = db.Column(db.String(40), nullable=True)
    family_friendly = db.Column(db.Boolean, nullable=False, default=False)
    popularity_score = db.Column(db.Float, nullable=False, default=0)

    reviews = db.relationship("Review", back_populates="place", cascade="all, delete-orphan")
    favourites = db.relationship("Favourite", back_populates="place", cascade="all, delete-orphan")


class Trip(db.Model):
    __tablename__ = "trips"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    city = db.Column(db.String(120), nullable=False, index=True)
    mood = db.Column(db.String(80), nullable=False)
    budget_level = db.Column(db.String(40), nullable=False)
    budget_amount = db.Column(db.Float, nullable=False, default=1000)
    num_days = db.Column(db.Integer, nullable=False)
    num_people = db.Column(db.Integer, nullable=False, default=1)
    origin_city = db.Column(db.String(120), nullable=True)
    travel_date = db.Column(db.String(10), nullable=True)
    start_location = db.Column(db.String(255), nullable=True)
    start_latitude = db.Column(db.Float, nullable=True)
    start_longitude = db.Column(db.Float, nullable=True)
    predicted_category = db.Column(db.String(120), nullable=True)
    estimated_trip_cost = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="planned")
    currency = db.Column(db.String(10), nullable=False, default="USD")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="trips")
    reviews = db.relationship("Review", back_populates="trip", cascade="all, delete-orphan")
    itinerary_stops = db.relationship(
        "ItineraryStop",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="ItineraryStop.visit_order",
    )


class ItineraryStop(db.Model):
    __tablename__ = "itinerary_stops"

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey("trips.id"), nullable=False, index=True)
    place_id = db.Column(db.Integer, db.ForeignKey("places.id"), nullable=False, index=True)
    visit_order = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    start_minutes = db.Column(db.Integer, nullable=False)
    end_minutes = db.Column(db.Integer, nullable=False)

    trip = db.relationship("Trip", back_populates="itinerary_stops")
    place = db.relationship("Place")


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    trip_id = db.Column(db.Integer, db.ForeignKey("trips.id"), nullable=False, index=True)
    place_id = db.Column(db.Integer, db.ForeignKey("places.id"), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="reviews")
    trip = db.relationship("Trip", back_populates="reviews")
    place = db.relationship("Place", back_populates="reviews")


class Favourite(db.Model):
    __tablename__ = "favourites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    place_id = db.Column(db.Integer, db.ForeignKey("places.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="favourites")
    place = db.relationship("Place", back_populates="favourites")

    __table_args__ = (db.UniqueConstraint("user_id", "place_id", name="unique_user_place_favourite"),)


