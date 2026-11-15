from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.auth.routes import login_required
from app.extensions import db
from app.models import Favourite, Review, Trip

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/")
@login_required
def index():
    trips = Trip.query.filter_by(user_id=g.user.id).order_by(Trip.created_at.desc()).all()
    favourites = Favourite.query.filter_by(user_id=g.user.id).order_by(Favourite.created_at.desc()).all()
    reviews = Review.query.filter_by(user_id=g.user.id).order_by(Review.created_at.desc()).all()

    rating_counts = {rating: 0 for rating in range(1, 6)}
    for review in reviews:
        rating_counts[review.rating] += 1

    average_rating = 0
    if reviews:
        average_rating = sum(review.rating for review in reviews) / len(reviews)

    return render_template(
        "profile/index.html",
        trips=trips,
        favourites=favourites,
        reviews=reviews,
        rating_counts=rating_counts,
        average_rating=average_rating,
    )


@profile_bp.route("/favourites/<int:favourite_id>/remove", methods=["POST"])
@login_required
def remove_favourite(favourite_id):
    favourite = Favourite.query.filter_by(id=favourite_id, user_id=g.user.id).first_or_404()
    db.session.delete(favourite)
    db.session.commit()
    flash("Removed from favourites.", "info")
    return redirect(url_for("profile.index"))


@profile_bp.route("/reviews/<int:review_id>", methods=["POST"])
@login_required
def update_review(review_id):
    review = Review.query.filter_by(id=review_id, user_id=g.user.id).first_or_404()

    if request.form.get("delete") == "1":
        db.session.delete(review)
        db.session.commit()
        flash("Review deleted.", "info")
        return redirect(url_for("profile.index"))

    try:
        rating = int(request.form.get("rating", review.rating))
    except ValueError:
        rating = review.rating
    review.rating = max(1, min(5, rating))
    review.comment = request.form.get("comment", "").strip()
    db.session.commit()
    flash("Review updated.", "success")
    return redirect(url_for("profile.index"))


@profile_bp.route("/settings", methods=["POST"])
@login_required
def update_settings():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name can’t be empty.", "danger")
        return redirect(url_for("profile.index"))

    g.user.name = name
    db.session.commit()
    flash("Profile updated.", "success")
    return redirect(url_for("profile.index"))
