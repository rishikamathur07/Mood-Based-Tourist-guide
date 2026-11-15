from flask import Flask

from app.config import Config
from app.extensions import db


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="../../frontend/templates",
        static_folder="../../frontend/static",
    )
    app.config.from_object(config_class)

    db.init_app(app)

    from app.auth.routes import auth_bp
    from app.api.routes import api_bp
    from app.main.routes import main_bp
    from app.profile.routes import profile_bp
    from app.tools.routes import tools_bp
    from app.trips.routes import trips_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(trips_bp, url_prefix="/trips")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(tools_bp, url_prefix="/tools")
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.context_processor
    def inject_settings():
        google_maps_key = app.config.get("GOOGLE_MAPS_API_KEY", "").strip()
        has_google_maps_key = bool(
            google_maps_key
            and "paste-your-real" not in google_maps_key
            and "add-your-key" not in google_maps_key
        )
        return {
            "google_maps_api_key": google_maps_key if has_google_maps_key else "",
            "has_google_maps_key": has_google_maps_key,
        }

    with app.app_context():
        ensure_schema()

    register_cli(app)

    return app


def ensure_schema():
    """Add lightweight SQLite columns introduced after the first create_all."""
    from sqlalchemy import inspect, text

    db.create_all()
    inspector = inspect(db.engine)
    if "trips" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("trips")}
    lightweight_columns = {
        "currency": "VARCHAR(10) DEFAULT 'USD'",
        "origin_city": "VARCHAR(120)",
        "travel_date": "VARCHAR(10)",
        "start_location": "VARCHAR(255)",
        "start_latitude": "FLOAT",
        "start_longitude": "FLOAT",
    }
    for name, definition in lightweight_columns.items():
        if name not in columns:
            db.session.execute(text(f"ALTER TABLE trips ADD COLUMN {name} {definition}"))
    db.session.commit()


def register_cli(app):
    from app.cli import import_places, init_db, reset_db

    app.cli.add_command(init_db)
    app.cli.add_command(reset_db)
    app.cli.add_command(import_places)
