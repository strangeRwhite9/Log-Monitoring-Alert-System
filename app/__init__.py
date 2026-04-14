"""Flask application factory."""

from pathlib import Path

from flask import Flask

from .config import Config
from .services.alert_store import init_alert_store


def create_app() -> Flask:
    """Create and configure the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure app-level storage paths exist before the first write.
    Path(app.config["LOGIN_LOG_FILE"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["ALERT_DB_FILE"]).parent.mkdir(parents=True, exist_ok=True)
    init_alert_store(app.config["ALERT_DB_FILE"])

    from .routes import main_bp

    app.register_blueprint(main_bp)

    if not app.config["NOTIFIER_API_TOKEN"]:
        app.logger.warning(
            "NOTIFIER_API_TOKEN is missing. The local notifier API will reject requests."
        )

    return app
